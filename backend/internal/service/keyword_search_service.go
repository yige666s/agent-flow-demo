package service

import (
	"context"

	"template-recommend/internal/models"
	"template-recommend/internal/repository"
)

type KeywordSearchService struct {
	templateRepo *repository.TemplateRepository
}

func NewKeywordSearchService(templateRepo *repository.TemplateRepository) *KeywordSearchService {
	return &KeywordSearchService{
		templateRepo: templateRepo,
	}
}

func (s *KeywordSearchService) Search(ctx context.Context, keywords []string, topK int) ([]models.Template, error) {
	return s.templateRepo.SearchByKeywords(ctx, keywords, topK)
}
