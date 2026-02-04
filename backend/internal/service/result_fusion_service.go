package service

import (
	"sort"

	"template-recommend/internal/models"
)

type ResultFusionService struct {
	k float64 // RRF parameter
}

func NewResultFusionService() *ResultFusionService {
	return &ResultFusionService{
		k: 60.0, // TODO: Make configurable
	}
}

type scoredTemplate struct {
	template models.Template
	score    float64
}

// Merge uses RRF (Reciprocal Rank Fusion) algorithm
func (s *ResultFusionService) Merge(
	vectorResults []models.Template,
	tagResults []models.Template,
	keywordResults []models.Template,
	topK int,
) []models.Template {
	scores := make(map[string]float64)
	templates := make(map[string]models.Template)

	// Vector search results scoring (weight: 0.5)
	for rank, tmpl := range vectorResults {
		score := 1.0 / (s.k + float64(rank+1))
		scores[tmpl.TemplateID] = scores[tmpl.TemplateID] + score*0.5
		templates[tmpl.TemplateID] = tmpl
	}

	// Tag filter results scoring (weight: 0.3)
	for rank, tmpl := range tagResults {
		score := 1.0 / (s.k + float64(rank+1))
		scores[tmpl.TemplateID] = scores[tmpl.TemplateID] + score*0.3
		templates[tmpl.TemplateID] = tmpl
	}

	// Keyword search results scoring (weight: 0.2)
	for rank, tmpl := range keywordResults {
		score := 1.0 / (s.k + float64(rank+1))
		scores[tmpl.TemplateID] = scores[tmpl.TemplateID] + score*0.2
		templates[tmpl.TemplateID] = tmpl
	}

	// Sort by score
	var scored []scoredTemplate
	for id, tmpl := range templates {
		tmpl.FinalScore = scores[id]
		scored = append(scored, scoredTemplate{
			template: tmpl,
			score:    scores[id],
		})
	}

	sort.Slice(scored, func(i, j int) bool {
		return scored[i].score > scored[j].score
	})

	// Return Top-K
	var result []models.Template
	for i := 0; i < topK && i < len(scored); i++ {
		result = append(result, scored[i].template)
	}

	return result
}
