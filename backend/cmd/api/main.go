package main

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/gin-gonic/gin"

	"template-recommend/internal/client"
	"template-recommend/internal/config"
	"template-recommend/internal/database"
	"template-recommend/internal/handler"
	"template-recommend/internal/repository"
	"template-recommend/internal/service"
)

func main() {
	// Load configuration
	cfg, err := config.Load()
	if err != nil {
		log.Fatalf("Failed to load config: %v", err)
	}

	// Initialize database
	db, err := database.InitDB(&cfg.Database)
	if err != nil {
		log.Fatalf("Failed to init database: %v", err)
	}

	// Initialize repositories
	templateRepo := repository.NewTemplateRepository(db)
	interactionRepo := repository.NewUserInteractionRepository(db)

	// Initialize AI service client
	// TODO: Configure AI service address from config
	aiServiceAddr := fmt.Sprintf("%s:%d", cfg.Agent.Host, cfg.Agent.Port)
	aiClient, err := client.NewAIServiceClient(aiServiceAddr)
	if err != nil {
		log.Fatalf("Failed to init AI client: %v", err)
	}
	defer aiClient.Close()

	// Initialize services
	vectorSvc, err := service.NewVectorSearchService(cfg, templateRepo)
	if err != nil {
		log.Fatalf("Failed to init vector search service: %v", err)
	}
	defer vectorSvc.Close()

	tagSvc := service.NewTagFilterService(templateRepo)
	keywordSvc := service.NewKeywordSearchService(templateRepo)
	fusionSvc := service.NewResultFusionService()

	recommendSvc := service.NewRecommendService(
		aiClient,
		vectorSvc,
		tagSvc,
		keywordSvc,
		fusionSvc,
		interactionRepo,
	)

	cacheSvc, err := service.NewCacheService(cfg, aiClient)
	if err != nil {
		log.Printf("Warning: Failed to init semantic cache service: %v", err)
	}
	defer func() {
		if cacheSvc != nil {
			cacheSvc.Close()
		}
	}()

	// Initialize handlers
	recommendHandler := handler.NewRecommendHandler(recommendSvc, cacheSvc)
	templateHandler := handler.NewTemplateHandler(templateRepo)

	// Setup router
	router := gin.Default()

	// CORS Middleware
	router.Use(func(c *gin.Context) {
		c.Writer.Header().Set("Access-Control-Allow-Origin", "*")
		c.Writer.Header().Set("Access-Control-Allow-Credentials", "true")
		c.Writer.Header().Set("Access-Control-Allow-Headers", "Content-Type, Content-Length, Accept-Encoding, X-CSRF-Token, Authorization, accept, origin, Cache-Control, X-Requested-With")
		c.Writer.Header().Set("Access-Control-Allow-Methods", "POST, OPTIONS, GET, PUT, DELETE")

		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(204)
			return
		}

		c.Next()
	})

	// Health check
	router.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"status": "ok"})
	})

	// API routes
	v1 := router.Group("/api/v1")
	{
		// Recommendation endpoints
		recommend := v1.Group("/recommend")
		{
			recommend.POST("", recommendHandler.Recommend)
			recommend.POST("/feedback", recommendHandler.SubmitFeedback)
		}

		// Template endpoints
		templates := v1.Group("/templates")
		{
			templates.GET("", templateHandler.ListTemplates)
			templates.GET("/:id", templateHandler.GetTemplate)
			templates.POST("", templateHandler.CreateTemplate)
			templates.PUT("/:id", templateHandler.UpdateTemplate)
			templates.DELETE("/:id", templateHandler.DeleteTemplate)
		}
	}

	// Start server
	addr := fmt.Sprintf("%s:%d", cfg.Server.Host, cfg.Server.Port)
	srv := &http.Server{
		Addr:         addr,
		Handler:      router,
		ReadTimeout:  cfg.Server.ReadTimeout,
		WriteTimeout: cfg.Server.WriteTimeout,
	}

	// Graceful shutdown
	go func() {
		log.Printf("Server starting on %s", addr)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("Failed to start server: %v", err)
		}
	}()

	// Wait for interrupt signal
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	log.Println("Shutting down server...")

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := srv.Shutdown(ctx); err != nil {
		log.Fatal("Server forced to shutdown:", err)
	}

	log.Println("Server exited")
}
