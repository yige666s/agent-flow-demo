package handler

import (
	"net/http"
	"time"

	"github.com/gin-gonic/gin"

	"template-recommend/internal/service"
)

type RecommendHandler struct {
	recommendSvc *service.RecommendService
	cacheSvc     *service.CacheService
}

func NewRecommendHandler(recommendSvc *service.RecommendService, cacheSvc *service.CacheService) *RecommendHandler {
	return &RecommendHandler{
		recommendSvc: recommendSvc,
		cacheSvc:     cacheSvc,
	}
}

type RecommendRequest struct {
	Query  string `json:"query" binding:"required,max=500"`
	UserID string `json:"user_id"`
	TopK   int    `json:"top_k" binding:"min=1,max=20"`
}

type RecommendResponse struct {
	Status          string                      `json:"status"`
	Query           string                      `json:"query"`
	Recommendations []service.TemplateWithScore `json:"recommendations"`
	Explanation     string                      `json:"explanation"`
	ResponseTimeMs  int64                       `json:"response_time_ms"`
}

func (h *RecommendHandler) Recommend(c *gin.Context) {
	startTime := time.Now()

	var req RecommendRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// Set default TopK
	if req.TopK == 0 {
		req.TopK = 5
	}

	ctx := c.Request.Context()

	// 1. Check cache
	cached, err := h.cacheSvc.GetRecommendation(ctx, req.Query)
	if err == nil && cached != nil {
		c.JSON(http.StatusOK, cached)
		return
	}

	// 2. Call recommendation service
	result, err := h.recommendSvc.Recommend(ctx, req.Query, req.UserID, req.TopK)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	// 3. Build response
	response := RecommendResponse{
		Status:          "success",
		Query:           req.Query,
		Recommendations: result.Templates,
		Explanation:     result.Explanation,
		ResponseTimeMs:  time.Since(startTime).Milliseconds(),
	}

	// 4. Cache result asynchronously
	go h.cacheSvc.CacheRecommendation(c.Copy(), req.Query, response)

	c.JSON(http.StatusOK, response)
}

type FeedbackRequest struct {
	UserID     string `json:"user_id" binding:"required"`
	Query      string `json:"query" binding:"required"`
	TemplateID string `json:"template_id"`
	Feedback   string `json:"feedback" binding:"required,oneof=positive negative neutral"`
}

func (h *RecommendHandler) SubmitFeedback(c *gin.Context) {
	var req FeedbackRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	ctx := c.Request.Context()

	if err := h.recommendSvc.SaveFeedback(ctx, req.UserID, req.Query, req.TemplateID, req.Feedback); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"status": "success"})
}
