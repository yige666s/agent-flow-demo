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

// Merge uses RRF (Reciprocal Rank Fusion) algorithm with dynamic weighting
func (s *ResultFusionService) Merge(
	vectorResults []models.Template,
	tagResults []models.Template,
	keywordResults []models.Template,
	topK int,
) []models.Template {
	scores := make(map[string]float64)
	templates := make(map[string]models.Template)

	// Determine weights based on which results are available
	vectorWeight := 0.5
	tagWeight := 0.3
	keywordWeight := 0.2

	// Dynamic weight adjustment: boost vector if it's the only source
	hasVector := len(vectorResults) > 0
	hasTag := len(tagResults) > 0
	hasKeyword := len(keywordResults) > 0

	if hasVector && !hasTag && !hasKeyword {
		vectorWeight = 1.0
	} else if hasTag && !hasVector && !hasKeyword {
		tagWeight = 1.0
	} else if hasKeyword && !hasVector && !hasTag {
		keywordWeight = 1.0
	} else if hasVector && hasTag && !hasKeyword {
		vectorWeight = 0.6
		tagWeight = 0.4
	}

	// Vector search results scoring
	for rank, tmpl := range vectorResults {
		score := (1.0 / (s.k + float64(rank+1))) * vectorWeight
		scores[tmpl.TemplateID] = scores[tmpl.TemplateID] + score
		templates[tmpl.TemplateID] = tmpl
	}

	// Tag filter results scoring
	for rank, tmpl := range tagResults {
		score := (1.0 / (s.k + float64(rank+1))) * tagWeight
		scores[tmpl.TemplateID] = scores[tmpl.TemplateID] + score
		templates[tmpl.TemplateID] = tmpl
	}

	// Keyword search results scoring
	for rank, tmpl := range keywordResults {
		score := (1.0 / (s.k + float64(rank+1))) * keywordWeight
		scores[tmpl.TemplateID] = scores[tmpl.TemplateID] + score
		templates[tmpl.TemplateID] = tmpl
	}

	// Add popularity boost based on use_count
	for id, tmpl := range templates {
		// Normalize use_count to [0, 0.1] range to avoid overwhelming other signals
		popularityBoost := float64(tmpl.UseCount) / 1000.0
		if popularityBoost > 0.1 {
			popularityBoost = 0.1
		}
		scores[id] = scores[id] + popularityBoost
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
