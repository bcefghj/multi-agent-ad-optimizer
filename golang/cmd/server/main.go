package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"strconv"

	"github.com/bcefghj/multi-agent-ad-optimizer/internal/orchestrator"
	"github.com/bcefghj/multi-agent-ad-optimizer/internal/service"
)

func main() {
	supervisor := orchestrator.NewSupervisor()

	http.HandleFunc("/api/v1/optimize", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}

		count, _ := strconv.Atoi(r.URL.Query().Get("campaigns"))
		if count <= 0 {
			count = 5
		}
		maxIter, _ := strconv.Atoi(r.URL.Query().Get("maxIterations"))
		if maxIter <= 0 {
			maxIter = 2
		}

		metrics := service.GenerateMetrics(count)
		result := supervisor.RunPipeline(metrics, maxIter)

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(result)
	})

	http.HandleFunc("/api/v1/metrics", func(w http.ResponseWriter, r *http.Request) {
		count, _ := strconv.Atoi(r.URL.Query().Get("count"))
		if count <= 0 {
			count = 5
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(service.GenerateMetrics(count))
	})

	http.HandleFunc("/api/v1/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		fmt.Fprintf(w, `{"status":"UP","service":"Multi-Agent Ad Optimizer (Go)"}`)
	})

	port := ":8081"
	log.Printf("Go server starting on %s", port)
	log.Fatal(http.ListenAndServe(port, nil))
}
