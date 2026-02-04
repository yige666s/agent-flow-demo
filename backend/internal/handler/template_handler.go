package handler

import (
	"net/http"
	"strconv"

	"github.com/gin-gonic/gin"

	"template-recommend/internal/models"
	"template-recommend/internal/repository"
)

type TemplateHandler struct {
	templateRepo *repository.TemplateRepository
}

func NewTemplateHandler(templateRepo *repository.TemplateRepository) *TemplateHandler {
	return &TemplateHandler{
		templateRepo: templateRepo,
	}
}

func (h *TemplateHandler) GetTemplate(c *gin.Context) {
	templateID := c.Param("id")

	ctx := c.Request.Context()
	template, err := h.templateRepo.GetByTemplateID(ctx, templateID)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Template not found"})
		return
	}

	// Increment view count
	go h.templateRepo.IncrementViewCount(c.Copy(), templateID)

	c.JSON(http.StatusOK, template)
}

func (h *TemplateHandler) ListTemplates(c *gin.Context) {
	limit, _ := strconv.Atoi(c.DefaultQuery("limit", "20"))
	offset, _ := strconv.Atoi(c.DefaultQuery("offset", "0"))

	ctx := c.Request.Context()
	templates, err := h.templateRepo.List(ctx, limit, offset)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"templates": templates,
		"limit":     limit,
		"offset":    offset,
	})
}

func (h *TemplateHandler) CreateTemplate(c *gin.Context) {
	var template models.Template
	if err := c.ShouldBindJSON(&template); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	ctx := c.Request.Context()
	if err := h.templateRepo.Create(ctx, &template); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusCreated, template)
}

func (h *TemplateHandler) UpdateTemplate(c *gin.Context) {
	templateID := c.Param("id")

	ctx := c.Request.Context()
	template, err := h.templateRepo.GetByTemplateID(ctx, templateID)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Template not found"})
		return
	}

	if err := c.ShouldBindJSON(template); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if err := h.templateRepo.Update(ctx, template); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, template)
}

func (h *TemplateHandler) DeleteTemplate(c *gin.Context) {
	templateID := c.Param("id")

	ctx := c.Request.Context()
	template, err := h.templateRepo.GetByTemplateID(ctx, templateID)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Template not found"})
		return
	}

	if err := h.templateRepo.Delete(ctx, template.ID); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"status": "deleted"})
}
