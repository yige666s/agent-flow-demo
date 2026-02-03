package main

import (
	"log"
	"time"

	"agentflow/agent"
	"agentflow/config"
	"agentflow/handlers"
	"agentflow/orchestrator"
	"agentflow/storage"

	"github.com/gin-gonic/gin"
)

func main() {
	// 1. 加载配置
	cfg, err := config.LoadConfig("../config.yaml")
	if err != nil {
		log.Fatalf("Failed to load config: %v", err)
	}

	// 2. 初始化存储层
	var store storage.Storage
	if cfg.Storage.Type == "json" {
		store, err = storage.NewJSONStorage(cfg.Storage.JSON.DataDir)
		if err != nil {
			log.Fatalf("Failed to create JSON storage: %v", err)
		}
		log.Println("Using JSON file storage")
	} else {
		log.Fatalf("Unsupported storage type: %s", cfg.Storage.Type)
	}

	// 3. 初始化 Agent 客户端
	agentClient := agent.NewClient(
		cfg.Agent.PythonServiceURL,
		time.Duration(cfg.Agent.RequestTimeout)*time.Second,
	)
	log.Printf("Agent client configured: %s", cfg.Agent.PythonServiceURL)

	// 4. 初始化编排器
	orch := orchestrator.NewOrchestrator(store, agentClient)

	// 5. 初始化 HTTP Handler
	handler := handlers.NewHandler(orch)

	// 6. 设置路由
	router := gin.Default()

	// CORS middleware for frontend
	router.Use(func(c *gin.Context) {
		c.Writer.Header().Set("Access-Control-Allow-Origin", "*")
		c.Writer.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
		c.Writer.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")

		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(204)
			return
		}

		c.Next()
	})

	// API v1
	v1 := router.Group("/api/v1")
	{
		v1.POST("/tasks", handler.CreateTask)
		v1.GET("/tasks/:id", handler.GetTask)
		v1.POST("/tasks/:id/cancel", handler.CancelTask)
	}

	// 健康检查
	router.GET("/health", handler.HealthCheck)

	// 7. 启动服务器
	addr := cfg.Server.GetAddress()
	log.Printf("Starting AgentFlow backend server on %s", addr)
	if err := router.Run(addr); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}
