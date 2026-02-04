package service

import (
	"context"
	"fmt"

	"github.com/milvus-io/milvus-sdk-go/v2/client"
	"github.com/milvus-io/milvus-sdk-go/v2/entity"

	"template-recommend/internal/config"
	"template-recommend/internal/models"
	"template-recommend/internal/repository"
)

type VectorSearchService struct {
	milvusClient   client.Client
	templateRepo   *repository.TemplateRepository
	collectionName string
	dimension      int
}

func NewVectorSearchService(cfg *config.MilvusConfig, templateRepo *repository.TemplateRepository) (*VectorSearchService, error) {
	// TODO: Configure Milvus connection parameters
	milvusClient, err := client.NewGrpcClient(
		context.Background(),
		fmt.Sprintf("%s:%d", cfg.Host, cfg.Port),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to connect to Milvus: %w", err)
	}

	svc := &VectorSearchService{
		milvusClient:   milvusClient,
		templateRepo:   templateRepo,
		collectionName: "templates",
		dimension:      1536, // TODO: Configure embedding dimension based on model
	}

	// Initialize collection if not exists
	if err := svc.initCollection(context.Background()); err != nil {
		return nil, fmt.Errorf("failed to init collection: %w", err)
	}

	return svc, nil
}

func (s *VectorSearchService) initCollection(ctx context.Context) error {
	has, err := s.milvusClient.HasCollection(ctx, s.collectionName)
	if err != nil {
		return err
	}

	if has {
		return nil
	}

	// Create collection
	schema := &entity.Schema{
		CollectionName: s.collectionName,
		Description:    "Template embeddings collection",
		Fields: []*entity.Field{
			{
				Name:       "id",
				DataType:   entity.FieldTypeInt64,
				PrimaryKey: true,
				AutoID:     true,
			},
			{
				Name:     "template_id",
				DataType: entity.FieldTypeVarChar,
				TypeParams: map[string]string{
					"max_length": "64",
				},
			},
			{
				Name:     "embedding",
				DataType: entity.FieldTypeFloatVector,
				TypeParams: map[string]string{
					"dim": fmt.Sprintf("%d", s.dimension),
				},
			},
		},
	}

	if err := s.milvusClient.CreateCollection(ctx, schema, entity.DefaultShardNumber); err != nil {
		return err
	}

	// Create index
	idx, err := entity.NewIndexHNSW(entity.L2, 16, 200)
	if err != nil {
		return err
	}

	if err := s.milvusClient.CreateIndex(ctx, s.collectionName, "embedding", idx, false); err != nil {
		return err
	}

	// Load collection
	if err := s.milvusClient.LoadCollection(ctx, s.collectionName, false); err != nil {
		return err
	}

	return nil
}

func (s *VectorSearchService) Search(ctx context.Context, embedding []float32, topK int) ([]models.Template, error) {
	// Search in Milvus
	searchParams, err := entity.NewIndexHNSWSearchParam(100)
	if err != nil {
		return nil, err
	}

	vectors := []entity.Vector{
		entity.FloatVector(embedding),
	}

	searchResult, err := s.milvusClient.Search(
		ctx,
		s.collectionName,
		nil,
		"",
		[]string{"template_id"},
		vectors,
		"embedding",
		entity.L2,
		topK,
		searchParams,
	)
	if err != nil {
		return nil, fmt.Errorf("milvus search failed: %w", err)
	}

	if len(searchResult) == 0 {
		return []models.Template{}, nil
	}

	// Extract template IDs and scores
	var templateIDs []string
	scoreMap := make(map[string]float32)

	for _, result := range searchResult[0].Fields {
		if result.Name() == "template_id" {
			column := result.(*entity.ColumnVarChar)
			for i := 0; i < column.Len(); i++ {
				val, _ := column.ValueByIdx(i)
				templateIDs = append(templateIDs, val)

				if i < len(searchResult[0].Scores) {
					scoreMap[val] = searchResult[0].Scores[i]
				}
			}
		}
	}

	// Get full template info from database
	templates, err := s.templateRepo.GetByIDs(ctx, templateIDs)
	if err != nil {
		return nil, fmt.Errorf("get templates failed: %w", err)
	}

	// Add vector scores
	for i := range templates {
		templates[i].VectorScore = scoreMap[templates[i].TemplateID]
	}

	return templates, nil
}

func (s *VectorSearchService) AddTemplates(ctx context.Context, templates []models.Template, embeddings [][]float32) error {
	if len(templates) != len(embeddings) {
		return fmt.Errorf("templates and embeddings length mismatch")
	}

	templateIDs := make([]string, len(templates))
	vectors := make([][]float32, len(embeddings))

	for i, tmpl := range templates {
		templateIDs[i] = tmpl.TemplateID
		vectors[i] = embeddings[i]
	}

	templateIDColumn := entity.NewColumnVarChar("template_id", templateIDs)
	embeddingColumn := entity.NewColumnFloatVector("embedding", s.dimension, vectors)

	if _, err := s.milvusClient.Insert(
		ctx,
		s.collectionName,
		"",
		templateIDColumn,
		embeddingColumn,
	); err != nil {
		return fmt.Errorf("failed to insert into Milvus: %w", err)
	}

	return nil
}

func (s *VectorSearchService) Close() {
	if s.milvusClient != nil {
		s.milvusClient.Close()
	}
}
