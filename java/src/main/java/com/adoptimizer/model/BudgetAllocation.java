package com.adoptimizer.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class BudgetAllocation {
    private String campaignId;
    private String campaignName;
    private double currentBudget;
    private double recommendedBudget;
    private double changePct;
    private String reason;
}
