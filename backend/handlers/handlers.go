package handlers

import (
	"net/http"

	"agentflow/models"
	"agentflow/orchestrator"

	"github.com/gin-gonic/gin"
)

// Handler API 处理器
type Handler struct {
	orch *orchestrator.Orchestrator
}

// NewHandler 创建 Handler 实例
func NewHandler(orch *orchestrator.Orchestrator) *Handler {
	return &Handler{
		orch: orch,
	}
}

// CreateTask 创建任务
func (h *Handler) CreateTask(c *gin.Context) {
	var req models.CreateTaskRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, models.ErrorResponse{
			Error: models.ErrorDetail{
				Code:    "INVALID_INPUT",
				Message: err.Error(),
			},
		})
		return
	}

	task, err := h.orch.CreateTask(req.UserInput, req.Metadata)
	if err != nil {
		c.JSON(http.StatusInternalServerError, models.ErrorResponse{
			Error: models.ErrorDetail{
				Code:    "CREATE_TASK_FAILED",
				Message: err.Error(),
			},
		})
		return
	}

	c.JSON(http.StatusCreated, models.CreateTaskResponse{
		TaskID:    task.ID,
		Status:    string(task.Status),
		CreatedAt: task.CreatedAt,
	})
}

// GetTask 获取任务
func (h *Handler) GetTask(c *gin.Context) {
	taskID := c.Param("id")

	task, err := h.orch.GetTask(taskID)
	if err != nil {
		c.JSON(http.StatusNotFound, models.ErrorResponse{
			Error: models.ErrorDetail{
				Code:    "TASK_NOT_FOUND",
				Message: err.Error(),
			},
		})
		return
	}

	c.JSON(http.StatusOK, task)
}

// CancelTask 取消任务
func (h *Handler) CancelTask(c *gin.Context) {
	taskID := c.Param("id")

	if err := h.orch.CancelTask(taskID); err != nil {
		c.JSON(http.StatusBadRequest, models.ErrorResponse{
			Error: models.ErrorDetail{
				Code:    "CANCEL_FAILED",
				Message: err.Error(),
			},
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"task_id": taskID,
		"status":  "cancelled",
		"message": "Task cancelled successfully",
	})
}

// HealthCheck 健康检查
func (h *Handler) HealthCheck(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"status":  "healthy",
		"version": "1.0.0",
	})
}
