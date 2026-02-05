package main

import (
	"context"
	"fmt"
	"log"

	"template-recommend/internal/client"
	"template-recommend/internal/config"
	"template-recommend/internal/database"
	"template-recommend/internal/models"
	"template-recommend/internal/repository"
	"template-recommend/internal/service"
)

func main() {
	log.Println("Starting data seeder...")

	// Load config
	cfg, err := config.Load()
	if err != nil {
		log.Fatalf("Failed to load config: %v", err)
	}

	// Connect to DB
	log.Println("Connecting to Database...")
	db, err := database.InitDB(&cfg.Database)
	if err != nil {
		log.Fatalf("Failed to connect to DB: %v", err)
	}

	templateRepo := repository.NewTemplateRepository(db)

	// Connect to AI Service
	log.Println("Connecting to AI Service...")
	aiAddr := fmt.Sprintf("%s:%d", cfg.Agent.Host, cfg.Agent.Port)
	aiClient, err := client.NewAIServiceClient(aiAddr)
	if err != nil {
		log.Fatalf("Failed to connect to AI service: %v", err)
	}
	defer aiClient.Close()

	// 1. Fetch all templates
	log.Println("Fetching templates from database...")
	templates, err := templateRepo.List(context.Background(), 1000, 0)
	if err != nil {
		log.Fatalf("Failed to list templates: %v", err)
	}

	if len(templates) == 0 {
		log.Println("No templates found in database. Please ensure init_db.sql was run.")
		return
	}

	// 2. Initial embedding to check dimension
	log.Println("Checking embedding dimension with AI Service...")
	sampleText := "test"
	sampleEmbedding, err := aiClient.GenerateEmbedding(context.Background(), sampleText)
	if err != nil {
		log.Fatalf("Failed to get sample embedding: %v", err)
	}
	actualDim := len(sampleEmbedding)
	log.Printf("Detected embedding dimension: %d", actualDim)

	// Update config dimension to match actual
	cfg.Agent.EmbeddingDim = actualDim

	// 3. Connect to Milvus
	log.Println("Connecting to Milvus...")
	vectorSvc, err := service.NewVectorSearchService(cfg, templateRepo)
	if err != nil {
		log.Fatalf("Failed to init vector service: %v", err)
	}
	defer vectorSvc.Close()

	// 4. Double check dimension and RECREATE if necessary
	// The problem is initCollection only creates if NOT exists.
	// We need to force recreate if the existing dimension is wrong.
	// OR just drop it every time we seed in this script.
	log.Println("Force recreating Milvus collection to ensure correct dimension...")
	if err := vectorSvc.DropCollection(context.Background()); err != nil {
		log.Printf("Warning: Failed to drop collection (might not exist): %v", err)
	}
	// Re-run init after drop
	// We need another way to trigger initCollection or just re-create the service
	vectorSvc.Close()
	vectorSvc, err = service.NewVectorSearchService(cfg, templateRepo)
	if err != nil {
		log.Fatalf("Failed to re-init vector service: %v", err)
	}

	// 5. Generate Embeddings for all templates
	var templatesToInsert []models.Template
	var embeddings [][]float32

	ctx := context.Background()
	for _, tmpl := range templates {
		// Enhanced text with more metadata for better semantic matching
		text := fmt.Sprintf("%s。%s。分类：%s。风格：%s。色调：%s。用途：%s。标签：%s",
			tmpl.Name,
			tmpl.Description,
			tmpl.Category,
			tmpl.Style,
			tmpl.ColorScheme,
			tmpl.UseCase,
			joinTags(tmpl.Tags),
		)

		log.Printf("Generating embedding for [%s]...", tmpl.Name)
		embedding, err := aiClient.GenerateEmbedding(ctx, text)
		if err != nil {
			log.Printf("  Error: %v", err)
			continue
		}

		if len(embedding) != actualDim {
			log.Printf("  Warning: Dimension mismatch for %s (expected %d, got %d). Skipping.", tmpl.Name, actualDim, len(embedding))
			continue
		}

		templatesToInsert = append(templatesToInsert, tmpl)
		embeddings = append(embeddings, embedding)
	}

	// 5. Insert into Milvus
	if len(templatesToInsert) > 0 {
		log.Printf("Inserting %d vectors into Milvus...\n", len(templatesToInsert))
		if err := vectorSvc.AddTemplates(ctx, templatesToInsert, embeddings); err != nil {
			log.Fatalf("Failed to insert into Milvus: %v", err)
		}
		log.Println("Successfully seeded Milvus!")
	} else {
		log.Println("No templates successfully processed.")
	}
}

func joinTags(tags []string) string {
	if len(tags) == 0 {
		return ""
	}
	result := ""
	for i, tag := range tags {
		if i > 0 {
			result += "、"
		}
		result += tag
	}
	return result
}
