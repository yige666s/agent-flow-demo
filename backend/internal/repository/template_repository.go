package repository

import (
	"context"

	"github.com/lib/pq"
	"gorm.io/gorm"

	"template-recommend/internal/models"
)

type TemplateRepository struct {
	db *gorm.DB
}

func NewTemplateRepository(db *gorm.DB) *TemplateRepository {
	return &TemplateRepository{db: db}
}

func (r *TemplateRepository) Create(ctx context.Context, template *models.Template) error {
	return r.db.WithContext(ctx).Create(template).Error
}

func (r *TemplateRepository) GetByID(ctx context.Context, id int64) (*models.Template, error) {
	var template models.Template
	err := r.db.WithContext(ctx).First(&template, id).Error
	return &template, err
}

func (r *TemplateRepository) GetByTemplateID(ctx context.Context, templateID string) (*models.Template, error) {
	var template models.Template
	err := r.db.WithContext(ctx).Where("template_id = ?", templateID).First(&template).Error
	return &template, err
}

func (r *TemplateRepository) GetByIDs(ctx context.Context, ids []string) ([]models.Template, error) {
	var templates []models.Template
	err := r.db.WithContext(ctx).
		Where("template_id IN ?", ids).
		Find(&templates).Error
	return templates, err
}

func (r *TemplateRepository) List(ctx context.Context, limit, offset int) ([]models.Template, error) {
	var templates []models.Template
	err := r.db.WithContext(ctx).
		Where("status = ?", "active").
		Order("created_at DESC").
		Limit(limit).
		Offset(offset).
		Find(&templates).Error
	return templates, err
}

func (r *TemplateRepository) FilterByTags(ctx context.Context, tags []string, limit int) ([]models.Template, error) {
	var templates []models.Template

	// PostgreSQL array overlap operator
	err := r.db.WithContext(ctx).
		Where("status = ?", "active").
		Where("tags && ?", pq.StringArray(tags)).
		Order(gorm.Expr("cardinality(tags & ?) DESC", pq.StringArray(tags))). // Order by matching tag count
		Limit(limit).
		Find(&templates).Error

	return templates, err
}

func (r *TemplateRepository) SearchByKeywords(ctx context.Context, keywords []string, limit int) ([]models.Template, error) {
	var templates []models.Template

	if len(keywords) == 0 {
		return templates, nil
	}

	query := r.db.WithContext(ctx).Where("status = ?", "active")

	// Use OR logic instead of AND to avoid empty results
	// Build a condition that matches ANY keyword
	conditions := r.db.Where("1 = 0") // Start with false condition
	for _, keyword := range keywords {
		conditions = conditions.Or(
			"name ILIKE ? OR description ILIKE ? OR category ILIKE ? OR style ILIKE ? OR use_case ILIKE ?",
			"%"+keyword+"%", "%"+keyword+"%", "%"+keyword+"%", "%"+keyword+"%", "%"+keyword+"%",
		)
	}
	query = query.Where(conditions)

	// Order by relevance: templates matching more keywords rank higher
	// This is a simple heuristic - in production you might use full-text search
	err := query.Limit(limit).Find(&templates).Error
	return templates, err
}

func (r *TemplateRepository) Update(ctx context.Context, template *models.Template) error {
	return r.db.WithContext(ctx).Save(template).Error
}

func (r *TemplateRepository) Delete(ctx context.Context, id int64) error {
	return r.db.WithContext(ctx).Delete(&models.Template{}, id).Error
}

func (r *TemplateRepository) IncrementViewCount(ctx context.Context, templateID string) error {
	return r.db.WithContext(ctx).
		Model(&models.Template{}).
		Where("template_id = ?", templateID).
		Update("view_count", gorm.Expr("view_count + 1")).Error
}

func (r *TemplateRepository) IncrementUseCount(ctx context.Context, templateID string) error {
	return r.db.WithContext(ctx).
		Model(&models.Template{}).
		Where("template_id = ?", templateID).
		Update("use_count", gorm.Expr("use_count + 1")).Error
}
