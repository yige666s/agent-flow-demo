package orchestrator

import (
	"fmt"
	"log"
	"time"

	"agentflow/agent"
	"agentflow/models"
	"agentflow/storage"
)

// Orchestrator 任务编排器
type Orchestrator struct {
	storage     storage.Storage
	agentClient *agent.Client
}

// NewOrchestrator 创建编排器实例
func NewOrchestrator(storage storage.Storage, agentClient *agent.Client) *Orchestrator {
	return &Orchestrator{
		storage:     storage,
		agentClient: agentClient,
	}
}

// CreateTask 创建新任务
func (o *Orchestrator) CreateTask(userInput string, metadata map[string]interface{}) (*models.Task, error) {
	task := &models.Task{
		ID:        generateTaskID(),
		UserInput: userInput,
		Status:    models.TaskStatusPending,
		CreatedAt: time.Now(),
		UpdatedAt: time.Now(),
		Metadata:  metadata,
	}

	if err := o.storage.SaveTask(task); err != nil {
		return nil, fmt.Errorf("failed to save task: %w", err)
	}

	// 异步执行任务
	go o.executeTask(task.ID)

	return task, nil
}

// GetTask 获取任务
func (o *Orchestrator) GetTask(taskID string) (*models.Task, error) {
	return o.storage.GetTask(taskID)
}

// ListTasks 获取任务列表（所有任务）
func (o *Orchestrator) ListTasks() ([]*models.Task, error) {
	// 空字符串状态 = 不过滤，0 limit = 无限制
	return o.storage.ListTasks("", 0)
}

// CancelTask 取消任务
func (o *Orchestrator) CancelTask(taskID string) error {
	task, err := o.storage.GetTask(taskID)
	if err != nil {
		return err
	}

	// 只能取消待处理或运行中的任务
	if task.Status != models.TaskStatusPending && task.Status != models.TaskStatusRunning {
		return fmt.Errorf("cannot cancel task in status: %s", task.Status)
	}

	return o.storage.UpdateTaskStatus(taskID, models.TaskStatusCancelled)
}

// executeTask 执行任务（内部方法）
func (o *Orchestrator) executeTask(taskID string) {
	log.Printf("Starting execution for task: %s", taskID)

	// 1. 获取任务
	task, err := o.storage.GetTask(taskID)
	if err != nil {
		log.Printf("Failed to get task %s: %v", taskID, err)
		return
	}

	// 2. 更新状态为 RUNNING（使用统一端点，无需单独 planning 状态）
	if err := o.storage.UpdateTaskStatus(taskID, models.TaskStatusRunning); err != nil {
		log.Printf("Failed to update task status to running: %v", err)
		return
	}

	// 3. 调用 Agent 统一执行端点（自动处理 planning 和 execution）
	runResp, err := o.agentClient.Run(taskID, task.UserInput, nil)
	if err != nil {
		log.Printf("Failed to run task %s: %v", taskID, err)
		o.storage.UpdateTaskError(taskID, fmt.Sprintf("Execution failed: %v", err))
		return
	}

	// 4. 保存执行计划（如果有）
	if runResp.Plan != nil {
		if err := o.storage.UpdateTaskPlan(taskID, runResp.Plan); err != nil {
			log.Printf("Failed to save plan for task %s: %v", taskID, err)
			// 继续执行，不中断
		}
	}

	// 5. 保存结果并更新状态为 COMPLETED
	if err := o.storage.UpdateTaskResult(taskID, runResp.Result); err != nil {
		log.Printf("Failed to save result for task %s: %v", taskID, err)
		return
	}

	if err := o.storage.UpdateTaskStatus(taskID, models.TaskStatusCompleted); err != nil {
		log.Printf("Failed to update task status to completed: %v", err)
		return
	}

	log.Printf("Task %s completed successfully (mode: %s)", taskID, runResp.Mode)
}

// generateTaskID 生成任务 ID
func generateTaskID() string {
	return fmt.Sprintf("task-%d", time.Now().UnixNano())
}
