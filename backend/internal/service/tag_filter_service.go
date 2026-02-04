package service

import (
	"context"

	"template-recommend/internal/models"
	"template-recommend/internal/repository"
)

type TagFilterService struct {
	templateRepo *repository.TemplateRepository
}

func NewTagFilterService(templateRepo *repository.TemplateRepository) *TagFilterService {
	return &TagFilterService{
		templateRepo: templateRepo,
	}
}

func (s *TagFilterService) FilterByTags(ctx context.Context, tags []string, topK int) ([]models.Template, error) {
	return s.templateRepo.FilterByTags(ctx, tags, topK)
}
