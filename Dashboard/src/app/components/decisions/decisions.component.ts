import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import { ScalingDecision } from '../../models/api.models';

@Component({
  selector: 'app-decisions',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './decisions.component.html',
  styleUrls: ['./decisions.component.css']
})
export class DecisionsComponent implements OnInit {
  decisions: ScalingDecision[] = [];
  loading = true;
  error: string | null = null;
  limit = 50;

  constructor(private apiService: ApiService) {}

  ngOnInit(): void {
    this.loadDecisions();
  }

  loadDecisions(): void {
    this.loading = true;
    this.error = null;

    this.apiService.getDecisions(this.limit).subscribe({
      next: (response) => {
        if (response.success) {
          this.decisions = response.decisions.reverse(); // Show newest first
        }
        this.loading = false;
      },
      error: (err) => {
        this.error = 'Failed to load decisions';
        this.loading = false;
        console.error(err);
      }
    });
  }

  getActionClass(action: string): string {
    switch (action) {
      case 'INCREASE':
        return 'badge-success';
      case 'DECREASE':
        return 'badge-danger';
      case 'MAINTAIN':
        return 'badge-info';
      default:
        return 'badge-secondary';
    }
  }

  getTimestamp(decision: ScalingDecision): string {
    return new Date(decision.timestamp).toLocaleString();
  }

  getConfidenceColor(confidence: number): string {
    if (confidence >= 0.8) return '#2ecc71';
    if (confidence >= 0.6) return '#f39c12';
    return '#e74c3c';
  }

  // Helper methods for new enhanced format
  getOverallAction(decision: ScalingDecision): string {
    if (decision.action) return decision.action;
    if (decision.cpu_action && decision.memory_action) {
      if (decision.cpu_action === 'INCREASE' || decision.memory_action === 'INCREASE') return 'INCREASE';
      if (decision.cpu_action === 'DECREASE' || decision.memory_action === 'DECREASE') return 'DECREASE';
      return 'MAINTAIN';
    }
    return 'MAINTAIN';
  }

  getOverallConfidence(decision: ScalingDecision): number {
    if (typeof decision.confidence === 'number') return decision.confidence;
    if (decision.confidence && typeof decision.confidence === 'object') {
      return (decision.confidence.cpu + decision.confidence.memory) / 2;
    }
    return 0;
  }

  // Type-safe accessors for template
  hasEnhancedFormat(decision: ScalingDecision): boolean {
    return !!(decision.cpu_action && decision.memory_action);
  }

  getConfidenceObject(decision: ScalingDecision): {cpu: number, memory: number} | null {
    if (decision.confidence && typeof decision.confidence === 'object') {
      return decision.confidence;
    }
    return null;
  }

  getCpuConfidence(decision: ScalingDecision): number {
    const conf = this.getConfidenceObject(decision);
    return conf ? conf.cpu : this.getOverallConfidence(decision);
  }

  getMemoryConfidence(decision: ScalingDecision): number {
    const conf = this.getConfidenceObject(decision);
    return conf ? conf.memory : this.getOverallConfidence(decision);
  }

  getCurrentCpuCores(decision: ScalingDecision): number {
    if (decision.current_resources?.cpu_cores) return decision.current_resources.cpu_cores;
    if (decision.current_metrics?.cpu_usage) return decision.current_metrics.cpu_usage;
    return 0;
  }

  getProposedCpuCores(decision: ScalingDecision): number {
    if (decision.proposed_resources?.cpu_cores) return decision.proposed_resources.cpu_cores;
    if (decision.resource_changes?.cpu?.new) return decision.resource_changes.cpu.new;
    return this.getCurrentCpuCores(decision);
  }

  getCurrentMemoryMb(decision: ScalingDecision): number {
    if (decision.current_resources?.memory_mb) return decision.current_resources.memory_mb;
    if (decision.current_metrics?.memory_usage_mb) return decision.current_metrics.memory_usage_mb;
    return 0;
  }

  getProposedMemoryMb(decision: ScalingDecision): number {
    if (decision.proposed_resources?.memory_mb) return decision.proposed_resources.memory_mb;
    if (decision.resource_changes?.memory?.new) return decision.resource_changes.memory.new;
    return this.getCurrentMemoryMb(decision);
  }

  getUsageCpuCores(decision: ScalingDecision): number {
    if (decision.current_usage?.cpu_cores) return decision.current_usage.cpu_cores;
    if (decision.current_metrics?.cpu_usage) return decision.current_metrics.cpu_usage;
    return 0;
  }

  getUsageMemoryMb(decision: ScalingDecision): number {
    if (decision.current_usage?.memory_mb) return decision.current_usage.memory_mb;
    if (decision.current_metrics?.memory_usage_mb) return decision.current_metrics.memory_usage_mb;
    return 0;
  }

  isApplied(decision: ScalingDecision): boolean {
    if (decision.applied !== undefined) return decision.applied;
    return decision.can_scale !== false;
  }

  getReason(decision: ScalingDecision): string {
    if (decision.reason) return decision.reason;
    if (decision.can_scale === false) return 'Scaling not allowed';
    const changes: string[] = [];
    if (decision.cpu_action && decision.cpu_action !== 'MAINTAIN') {
      changes.push(`CPU: ${decision.cpu_action}`);
    }
    if (decision.memory_action && decision.memory_action !== 'MAINTAIN') {
      changes.push(`Memory: ${decision.memory_action}`);
    }
    return changes.length > 0 ? changes.join(', ') : 'No changes needed';
  }

  // Safe accessors for resource changes
  getCpuChangePercent(decision: ScalingDecision): number {
    return decision.resource_changes?.cpu?.change_percent || 0;
  }

  getMemoryChangePercent(decision: ScalingDecision): number {
    return decision.resource_changes?.memory?.change_percent || 0;
  }

  hasCpuChanges(decision: ScalingDecision): boolean {
    return !!(decision.resource_changes?.cpu && decision.resource_changes.cpu.change_percent !== 0);
  }

  hasMemoryChanges(decision: ScalingDecision): boolean {
    return !!(decision.resource_changes?.memory && decision.resource_changes.memory.change_percent !== 0);
  }
}
