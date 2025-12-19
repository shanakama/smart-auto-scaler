import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../services/api.service';
import { Pod } from '../../models/api.models';

@Component({
  selector: 'app-pods',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './pods.component.html',
  styleUrls: ['./pods.component.css']
})
export class PodsComponent implements OnInit {
  pods: Pod[] = [];
  loading = true;
  error: string | null = null;
  scalingPod: string | null = null;

  constructor(private apiService: ApiService) {}

  ngOnInit(): void {
    this.loadPods();
  }

  loadPods(): void {
    this.loading = true;
    this.error = null;

    this.apiService.getPods().subscribe({
      next: (response) => {
        if (response.success) {
          this.pods = response.pods;
        }
        this.loading = false;
      },
      error: (err) => {
        this.error = 'Failed to load pods';
        this.loading = false;
        console.error(err);
      }
    });
  }

  scalePod(pod: Pod): void {
    if (confirm(`Scale pod ${pod.name} in namespace ${pod.namespace}?`)) {
      this.scalingPod = `${pod.namespace}/${pod.name}`;

      this.apiService.scalePod(pod.namespace, pod.name).subscribe({
        next: (response) => {
          if (response.success) {
            const result = response.result;
            const confidence = typeof result.confidence === 'number' 
              ? result.confidence 
              : result.confidence 
                ? (result.confidence.cpu + result.confidence.memory) / 2 
                : 0;

            alert(
              `Scaling Decision:\n\n` +
              `Action: ${result.action || (result.cpu_action && result.memory_action ? `CPU: ${result.cpu_action}, Memory: ${result.memory_action}` : 'Unknown')}\n` +
              `Confidence: ${(confidence * 100).toFixed(1)}%\n` +
              `Current CPU: ${result.current_resources?.cpu_cores || result.current_metrics?.cpu_usage || 'N/A'} cores\n` +
              `Proposed CPU: ${result.proposed_resources?.cpu_cores || result.resource_changes?.cpu?.new || 'N/A'} cores\n` +
              `Current Memory: ${result.current_resources?.memory_mb || result.current_metrics?.memory_usage_mb || 'N/A'} MB\n` +
              `Proposed Memory: ${result.proposed_resources?.memory_mb || result.resource_changes?.memory?.new || 'N/A'} MB\n` +
              `Applied: ${result.applied !== undefined ? (result.applied ? 'Yes' : 'No') : (result.can_scale !== false ? 'Yes' : 'No')}\n` +
              `Reason: ${result.reason || (result.can_scale === false ? 'Scaling not allowed' : 'Auto-scaling decision')}`
            );
          }
          this.scalingPod = null;
        },
        error: (err) => {
          alert('Failed to scale pod: ' + err.message);
          this.scalingPod = null;
        }
      });
    }
  }

  getPodKey(pod: Pod): string {
    return `${pod.namespace}/${pod.name}`;
  }

  isScaling(pod: Pod): boolean {
    return this.scalingPod === this.getPodKey(pod);
  }
}
