package agent

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"

	"agentflow/models"
)

// Client Agent 服务客户端
type Client struct {
	baseURL string
	timeout time.Duration
	client  *http.Client
}

// NewClient 创建 Agent 客户端
func NewClient(baseURL string, timeout time.Duration) *Client {
	return &Client{
		baseURL: baseURL,
		timeout: timeout,
		client: &http.Client{
			Timeout: timeout,
		},
	}
}

// RunRequest 统一执行请求（支持所有模式）
type RunRequest struct {
	TaskID    string                 `json:"task_id"`
	UserInput string                 `json:"user_input"`
	Context   map[string]interface{} `json:"context,omitempty"`
}

// RunResponse 统一执行响应
type RunResponse struct {
	Status      string                 `json:"status"`
	TaskID      string                 `json:"task_id"`
	Mode        string                 `json:"mode,omitempty"`
	Plan        *models.Plan           `json:"plan,omitempty"`
	Result      map[string]interface{} `json:"result"`
	StepResults []interface{}          `json:"step_results,omitempty"`
	Error       string                 `json:"error,omitempty"`
}

// PlanRequest 任务拆解请求（Legacy 模式）
type PlanRequest struct {
	TaskID    string `json:"task_id"`
	UserInput string `json:"user_input"`
}

// PlanResponse 任务拆解响应（Legacy 模式）
type PlanResponse struct {
	Status string       `json:"status"`
	TaskID string       `json:"task_id"`
	Plan   *models.Plan `json:"plan"`
	Error  string       `json:"error,omitempty"`
}

// ExecuteRequest 任务执行请求（Legacy 模式）
type ExecuteRequest struct {
	TaskID  string                 `json:"task_id"`
	Plan    *models.Plan           `json:"plan"`
	Context map[string]interface{} `json:"context,omitempty"`
}

// ExecuteResponse 任务执行响应
type ExecuteResponse struct {
	Status  string                 `json:"status"`
	TaskID  string                 `json:"task_id"`
	Result  map[string]interface{} `json:"result"`
	Context map[string]interface{} `json:"context"`
	Error   string                 `json:"error,omitempty"`
}

// Run 统一执行入口（推荐使用，支持所有 Agent 模式）
func (c *Client) Run(taskID, userInput string, context map[string]interface{}) (*RunResponse, error) {
	req := RunRequest{
		TaskID:    taskID,
		UserInput: userInput,
		Context:   context,
	}

	body, err := json.Marshal(req)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	resp, err := c.client.Post(
		c.baseURL+"/agent/run",
		"application/json",
		bytes.NewBuffer(body),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to call agent service: %w", err)
	}
	defer resp.Body.Close()

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response: %w", err)
	}

	var runResp RunResponse
	if err := json.Unmarshal(respBody, &runResp); err != nil {
		return nil, fmt.Errorf("failed to unmarshal response: %w", err)
	}

	if runResp.Status == "failed" {
		return nil, fmt.Errorf("execution failed: %s", runResp.Error)
	}

	return &runResp, nil
}

// Plan 调用 Agent 进行任务拆解（Legacy 模式）
func (c *Client) Plan(taskID, userInput string) (*models.Plan, error) {
	req := PlanRequest{
		TaskID:    taskID,
		UserInput: userInput,
	}

	body, err := json.Marshal(req)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	resp, err := c.client.Post(
		c.baseURL+"/agent/plan",
		"application/json",
		bytes.NewBuffer(body),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to call agent service: %w", err)
	}
	defer resp.Body.Close()

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response: %w", err)
	}

	var planResp PlanResponse
	if err := json.Unmarshal(respBody, &planResp); err != nil {
		return nil, fmt.Errorf("failed to unmarshal response: %w", err)
	}

	if planResp.Status != "success" {
		return nil, fmt.Errorf("planning failed: %s", planResp.Error)
	}

	return planResp.Plan, nil
}

// Execute 调用 Agent 执行任务
func (c *Client) Execute(taskID string, plan *models.Plan, context map[string]interface{}) (map[string]interface{}, error) {
	req := ExecuteRequest{
		TaskID:  taskID,
		Plan:    plan,
		Context: context,
	}

	body, err := json.Marshal(req)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	resp, err := c.client.Post(
		c.baseURL+"/agent/execute",
		"application/json",
		bytes.NewBuffer(body),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to call agent service: %w", err)
	}
	defer resp.Body.Close()

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response: %w", err)
	}

	var execResp ExecuteResponse
	if err := json.Unmarshal(respBody, &execResp); err != nil {
		return nil, fmt.Errorf("failed to unmarshal response: %w", err)
	}

	if execResp.Status == "failed" {
		return nil, fmt.Errorf("execution failed: %s", execResp.Error)
	}

	return execResp.Result, nil
}

// HealthCheck 健康检查
func (c *Client) HealthCheck() error {
	resp, err := c.client.Get(c.baseURL + "/health")
	if err != nil {
		return fmt.Errorf("health check failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("agent service unhealthy: status %d", resp.StatusCode)
	}

	return nil
}
