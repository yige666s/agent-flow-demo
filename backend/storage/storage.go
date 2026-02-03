package storage

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sync"

	"agentflow/models"
)

// Storage 存储接口
type Storage interface {
	SaveTask(task *models.Task) error
	GetTask(taskID string) (*models.Task, error)
	UpdateTaskStatus(taskID string, status models.TaskStatus) error
	UpdateTaskPlan(taskID string, plan *models.Plan) error
	UpdateTaskResult(taskID string, result map[string]interface{}) error
	UpdateTaskError(taskID string, errMsg string) error
	ListTasks(status models.TaskStatus, limit int) ([]*models.Task, error)
}

// JSONStorage JSON 文件存储实现
type JSONStorage struct {
	dataDir string
	logDir  string // 日志目录
	userDir string // 用户文件目录
	mu      sync.RWMutex
}

// NewJSONStorage 创建 JSON 存储实例
func NewJSONStorage(dataDir string) (*JSONStorage, error) {
	// 创建主数据目录
	if err := os.MkdirAll(dataDir, 0755); err != nil {
		return nil, fmt.Errorf("failed to create data directory: %w", err)
	}

	// 创建日志目录
	logDir := filepath.Join(dataDir, "log")
	if err := os.MkdirAll(logDir, 0755); err != nil {
		return nil, fmt.Errorf("failed to create log directory: %w", err)
	}

	// 创建用户文件目录
	userDir := filepath.Join(dataDir, "user")
	if err := os.MkdirAll(userDir, 0755); err != nil {
		return nil, fmt.Errorf("failed to create user directory: %w", err)
	}

	return &JSONStorage{
		dataDir: dataDir,
		logDir:  logDir,
		userDir: userDir,
	}, nil
}

// SaveTask 保存任务
func (s *JSONStorage) SaveTask(task *models.Task) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	filePath := s.getTaskFilePath(task.ID)
	data, err := json.MarshalIndent(task, "", "  ")
	if err != nil {
		return fmt.Errorf("failed to marshal task: %w", err)
	}

	if err := os.WriteFile(filePath, data, 0644); err != nil {
		return fmt.Errorf("failed to write task file: %w", err)
	}

	return nil
}

// GetTask 获取任务
func (s *JSONStorage) GetTask(taskID string) (*models.Task, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	filePath := s.getTaskFilePath(taskID)
	data, err := os.ReadFile(filePath)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, fmt.Errorf("task not found: %s", taskID)
		}
		return nil, fmt.Errorf("failed to read task file: %w", err)
	}

	var task models.Task
	if err := json.Unmarshal(data, &task); err != nil {
		return nil, fmt.Errorf("failed to unmarshal task: %w", err)
	}

	return &task, nil
}

// UpdateTaskStatus 更新任务状态
func (s *JSONStorage) UpdateTaskStatus(taskID string, status models.TaskStatus) error {
	task, err := s.GetTask(taskID)
	if err != nil {
		return err
	}

	task.Status = status
	task.UpdatedAt = getCurrentTime()

	if status == models.TaskStatusCompleted || status == models.TaskStatusFailed || status == models.TaskStatusCancelled {
		now := getCurrentTime()
		task.CompletedAt = &now
	}

	return s.SaveTask(task)
}

// UpdateTaskPlan 更新任务计划
func (s *JSONStorage) UpdateTaskPlan(taskID string, plan *models.Plan) error {
	task, err := s.GetTask(taskID)
	if err != nil {
		return err
	}

	task.Plan = plan
	task.UpdatedAt = getCurrentTime()

	return s.SaveTask(task)
}

// UpdateTaskResult 更新任务结果
func (s *JSONStorage) UpdateTaskResult(taskID string, result map[string]interface{}) error {
	task, err := s.GetTask(taskID)
	if err != nil {
		return err
	}

	task.Result = result
	task.UpdatedAt = getCurrentTime()

	return s.SaveTask(task)
}

// UpdateTaskError 更新任务错误信息
func (s *JSONStorage) UpdateTaskError(taskID string, errMsg string) error {
	task, err := s.GetTask(taskID)
	if err != nil {
		return err
	}

	task.Error = errMsg
	task.Status = models.TaskStatusFailed
	task.UpdatedAt = getCurrentTime()
	now := getCurrentTime()
	task.CompletedAt = &now

	return s.SaveTask(task)
}

// ListTasks 列出任务
func (s *JSONStorage) ListTasks(status models.TaskStatus, limit int) ([]*models.Task, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	files, err := os.ReadDir(s.logDir)
	if err != nil {
		return nil, fmt.Errorf("failed to read log directory: %w", err)
	}

	var tasks []*models.Task
	for _, file := range files {
		if file.IsDir() || filepath.Ext(file.Name()) != ".json" {
			continue
		}

		taskID := file.Name()[:len(file.Name())-5] // 去掉 .json
		task, err := s.GetTask(taskID)
		if err != nil {
			continue
		}

		if status == "" || task.Status == status {
			tasks = append(tasks, task)
		}

		if limit > 0 && len(tasks) >= limit {
			break
		}
	}

	return tasks, nil
}

// getTaskFilePath 获取任务日志文件路径（存储任务日志）
func (s *JSONStorage) getTaskFilePath(taskID string) string {
	return filepath.Join(s.logDir, taskID+".json")
}

// GetUserFilePath 获取用户文件路径（存储用户生成的文件）
func (s *JSONStorage) GetUserFilePath(filename string) string {
	return filepath.Join(s.userDir, filename)
}
