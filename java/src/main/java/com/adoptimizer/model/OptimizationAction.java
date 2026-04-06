package com.adoptimizer.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class OptimizationAction {
    private String actionType;
    private String campaignId;
    private String targetId;
    private String beforeValue;
    private String afterValue;
    private String reason;
    private double confidence;
}
