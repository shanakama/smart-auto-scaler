import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { interval, Subscription } from 'rxjs';
import { switchMap } from 'rxjs/operators';
import { ApiService } from '../../services/api.service';
import { Statistics, AutoscaleStatus, Config } from '../../models/api.models';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.css']
})
export class DashboardComponent implements OnInit, OnDestroy {
  statistics: Statistics | null = null;
  autoscaleStatus: AutoscaleStatus | null = null;
  config: Config | null = null;
  loading = true;
  error: string | null = null;

  private refreshSubscription?: Subscription;

  constructor(private apiService: ApiService) {}

  ngOnInit(): void {
    this.loadDashboard();

    // Refresh every 10 seconds
    this.refreshSubscription = interval(10000)
      .pipe(switchMap(() => this.apiService.getStatistics()))
      .subscribe({
        next: (response) => {
          if (response.success) {
            this.statistics = response.statistics;
          }
        },
        error: (err) => console.error('Error refreshing statistics:', err)
      });
  }

  ngOnDestroy(): void {
    this.refreshSubscription?.unsubscribe();
  }

  loadDashboard(): void {
    this.loading = true;
    this.error = null;

    // Load statistics
    this.apiService.getStatistics().subscribe({
      next: (response) => {
        if (response.success) {
          this.statistics = response.statistics;
        }
      },
      error: (err) => {
        this.error = 'Failed to load statistics';
        console.error(err);
      }
    });

    // Load autoscale status
    this.apiService.getAutoscaleStatus().subscribe({
      next: (status) => {
        this.autoscaleStatus = status;
      },
      error: (err) => console.error('Failed to load autoscale status:', err)
    });

    // Load config
    this.apiService.getConfig().subscribe({
      next: (config) => {
        this.config = config;
        this.loading = false;
      },
      error: (err) => {
        this.error = 'Failed to load configuration';
        this.loading = false;
        console.error(err);
      }
    });
  }

  toggleAutoscale(): void {
    if (!this.autoscaleStatus) return;

    const action = this.autoscaleStatus.enabled
      ? this.apiService.stopAutoscale()
      : this.apiService.startAutoscale();

    action.subscribe({
      next: (response) => {
        if (response.success) {
          this.loadDashboard();
        }
      },
      error: (err) => {
        this.error = 'Failed to toggle autoscale';
        console.error(err);
      }
    });
  }

  scaleAllNow(): void {
    this.apiService.scaleAllPods().subscribe({
      next: (response) => {
        if (response.success) {
          alert(`Processed ${response.processed} pods successfully!`);
          this.loadDashboard();
        }
      },
      error: (err) => {
        this.error = 'Failed to scale pods';
        console.error(err);
      }
    });
  }

  getCpuActionCount(action: 'DECREASE' | 'MAINTAIN' | 'INCREASE'): number {
    if (!this.statistics?.action_distribution?.cpu_actions) return 0;
    return this.statistics.action_distribution.cpu_actions[action] || 0;
  }

  getMemoryActionCount(action: 'DECREASE' | 'MAINTAIN' | 'INCREASE'): number {
    if (!this.statistics?.action_distribution?.memory_actions) return 0;
    return this.statistics.action_distribution.memory_actions[action] || 0;
  }

  getCpuActionPercentage(action: 'DECREASE' | 'MAINTAIN' | 'INCREASE'): number {
    if (!this.statistics?.action_distribution?.cpu_actions) return 0;
    const total = this.getCpuActionCount('DECREASE') + this.getCpuActionCount('MAINTAIN') + this.getCpuActionCount('INCREASE');
    if (total === 0) return 0;
    return Math.round((this.getCpuActionCount(action) / total) * 100);
  }

  getMemoryActionPercentage(action: 'DECREASE' | 'MAINTAIN' | 'INCREASE'): number {
    if (!this.statistics?.action_distribution?.memory_actions) return 0;
    const total = this.getMemoryActionCount('DECREASE') + this.getMemoryActionCount('MAINTAIN') + this.getMemoryActionCount('INCREASE');
    if (total === 0) return 0;
    return Math.round((this.getMemoryActionCount(action) / total) * 100);
  }
}
