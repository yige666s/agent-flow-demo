package service

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"golang.org/x/sync/errgroup"

	"template-recommend/internal/client"
	"template-recommend/internal/models"
	"template-recommend/internal/repository"
)

type RecommendService struct {
	aiClient        *client.AIServiceClient
	vectorSvc       *VectorSearchService
	tagSvc          *TagFilterService
	keywordSvc      *KeywordSearchService
	fusionSvc       *ResultFusionService
	interactionRepo *repository.UserInteractionRepository
}

func NewRecommendService(
	aiClient *client.AIServiceClient,
	vectorSvc *VectorSearchService,
	tagSvc *TagFilterService,
	keywordSvc *KeywordSearchService,
	fusionSvc *ResultFusionService,
	interactionRepo *repository.UserInteractionRepository,
) *RecommendService {
	return &RecommendService{
		aiClient:        aiClient,
		vectorSvc:       vectorSvc,
		tagSvc:          tagSvc,
		keywordSvc:      keywordSvc,
		fusionSvc:       fusionSvc,
		interactionRepo: interactionRepo,
	}
}

type TemplateWithScore struct {
	models.Template
	Score float64 `json:"score"`
}

type RecommendResult struct {
	Templates   []TemplateWithScore
	Explanation string
	Intent      *models.Intent
}

func (s *RecommendService) Recommend(
	ctx context.Context,
	query string,
	userID string,
	topK int,
) (*RecommendResult, error) {
	startTime := time.Now()

	// 1. Call Python AI service to understand intent
	intent, err := s.aiClient.UnderstandIntent(ctx, query, userID)
	if err != nil {
		return nil, fmt.Errorf("intent understanding failed: %w", err)
	}

	// 2. Parallel search based on strategy
	var (
		vectorResults  []models.Template
		tagResults     []models.Template
		keywordResults []models.Template
	)

	g, gctx := errgroup.WithContext(ctx)

	// Vector search
	if intent.SearchStrategy == "vector" || intent.SearchStrategy == "hybrid" {
		g.Go(func() error {
			// Generate embedding first
			embedding, err := s.aiClient.GenerateEmbedding(gctx, query)
			if err != nil {
				return err
			}

			// Vector search
			vectorResults, err = s.vectorSvc.Search(gctx, embedding, topK*2)
			return err
		})
	}

	// Tag filtering
	if len(intent.Tags) > 0 {
		g.Go(func() error {
			var err error
			tagResults, err = s.tagSvc.FilterByTags(gctx, intent.Tags, topK*2)
			return err
		})
	}

	// Keyword search
	if len(intent.Keywords) > 0 {
		g.Go(func() error {
			var err error
			keywordResults, err = s.keywordSvc.Search(gctx, intent.Keywords, topK)
			return err
		})
	}

	// Wait for all searches to complete
	if err := g.Wait(); err != nil {
		return nil, fmt.Errorf("search failed: %w", err)
	}

	// 3. Merge and rank results
	fusedResults := s.fusionSvc.Merge(vectorResults, tagResults, keywordResults, topK)

	// 4. Generate explanation
	explanation, err := s.aiClient.GenerateExplanation(ctx, query, fusedResults)
	if err != nil {
		// Explanation failure doesn't affect main flow
		explanation = "为您推荐以下模版"
	}

	// 5. Convert to TemplateWithScore
	var templatesWithScore []TemplateWithScore
	for _, tmpl := range fusedResults {
		templatesWithScore = append(templatesWithScore, TemplateWithScore{
			Template: tmpl,
			Score:    tmpl.FinalScore,
		})
	}

	// 6. Save interaction record asynchronously
	go s.saveInteraction(context.Background(), userID, query, intent, fusedResults, time.Since(startTime))

	return &RecommendResult{
		Templates:   templatesWithScore,
		Explanation: explanation,
		Intent:      intent,
	}, nil
}

func (s *RecommendService) saveInteraction(
	ctx context.Context,
	userID string,
	query string,
	intent *models.Intent,
	templates []models.Template,
	responseTime time.Duration,
) {
	intentJSON, _ := json.Marshal(intent)

	var templateIDs []string
	for _, tmpl := range templates {
		templateIDs = append(templateIDs, tmpl.TemplateID)
	}
	templatesJSON, _ := json.Marshal(templateIDs)

	interaction := &models.UserInteraction{
		UserID:               userID,
		Query:                query,
		Intent:               string(intentJSON),
		RecommendedTemplates: string(templatesJSON),
		ResponseTimeMs:       int(responseTime.Milliseconds()),
	}

	_ = s.interactionRepo.Create(ctx, interaction)
}

func (s *RecommendService) SaveFeedback(
	ctx context.Context,
	userID string,
	query string,
	templateID string,
	feedback string,
) error {
	// TODO: Implement feedback saving logic
	return nil
}
