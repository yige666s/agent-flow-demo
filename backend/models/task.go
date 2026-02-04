package models

import "time"

// TaskStatus 任务状态枚举
type TaskStatus string

const (
	TaskStatusPending   TaskStatus = "pending"
	TaskStatusPlanning  TaskStatus = "planning"
	TaskStatusRunning   TaskStatus = "running"
	TaskStatusCompleted TaskStatus = "completed"
	TaskStatusFailed    TaskStatus = "failed"
	TaskStatusCancelled TaskStatus = "cancelled"
)

// Task 任务实体
type Task struct {
	ID          string                 `json:"id"`
	UserInput   string                 `json:"user_input"`
	Status      TaskStatus             `json:"status"`
	Plan        *Plan                  `json:"plan,omitempty"`
	Result      map[string]interface{} `json:"result,omitempty"`
	Error       string                 `json:"error,omitempty"`
	CreatedAt   time.Time              `json:"created_at"`
	UpdatedAt   time.Time              `json:"updated_at"`
	CompletedAt *time.Time             `json:"completed_at,omitempty"`
	Metadata    map[string]interface{} `json:"metadata"`
}

// Plan 执行计划
type Plan struct {
	TaskID string `json:"task_id"`
	Steps  []Step `json:"steps"`
}

// Step 执行步骤
type Step struct {
	StepID         int                    `json:"step_id"`
	Description    string                 `json:"description"`
	Tool           string                 `json:"tool"`
	Parameters     map[string]interface{} `json:"parameters"`
	ExpectedOutput string                 `json:"expected_output"`
	Dependencies   []int                  `json:"dependencies"`
}

// StepResult 步骤执行结果
type StepResult struct {
	StepID    int                    `json:"step_id"`
	Status    string                 `json:"status"` // success / failed / skipped
	Output    interface{}            `json:"output"`
	Error     string                 `json:"error,omitempty"`
	StartTime time.Time              `json:"start_time"`
	EndTime   time.Time              `json:"end_time"`
	Duration  float64                `json:"duration"` // 秒
	Metadata  map[string]interface{} `json:"metadata,omitempty"`
}

// CreateTaskRequest 创建任务请求
type CreateTaskRequest struct {
	UserInput string                 `json:"user_input" binding:"required"`
	Metadata  map[string]interface{} `json:"metadata,omitempty"`
}

// CreateTaskResponse 创建任务响应
type CreateTaskResponse struct {
	TaskID    string    `json:"task_id"`
	Status    string    `json:"status"`
	CreatedAt time.Time `json:"created_at"`
}

// ErrorResponse 错误响应
type ErrorResponse struct {
	Error ErrorDetail `json:"error"`
}

// ErrorDetail 错误详情
type ErrorDetail struct {
	Code    string                 `json:"code"`
	Message string                 `json:"message"`
	Details map[string]interface{} `json:"details,omitempty"`
}
