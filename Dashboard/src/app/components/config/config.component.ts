import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import { Config } from '../../models/api.models';

@Component({
  selector: 'app-config',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './config.component.html',
  styleUrls: ['./config.component.css']
})
export class ConfigComponent implements OnInit {
  config: Config | null = null;
  loading = true;
  error: string | null = null;
  success: string | null = null;
  saving = false;

  constructor(private apiService: ApiService) {}

  ngOnInit(): void {
    this.loadConfig();
  }

  loadConfig(): void {
    this.loading = true;
    this.error = null;

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

  saveConfig(): void {
    if (!this.config) return;

    this.saving = true;
    this.error = null;
    this.success = null;

    const updates = {
      dry_run: this.config.dry_run,
      scale_factor: this.config.scale_factor,
      auto_scale_enabled: this.config.auto_scale_enabled,
      auto_scale_interval: this.config.auto_scale_interval,
      scaling_cooldown: this.config.scaling_cooldown,
      namespaces: this.config.namespaces
    };

    this.apiService.updateConfig(updates).subscribe({
      next: (response) => {
        if (response.success) {
          this.success = 'Configuration updated successfully!';
          setTimeout(() => this.success = null, 3000);
        }
        this.saving = false;
      },
      error: (err) => {
        this.error = 'Failed to update configuration';
        this.saving = false;
        console.error(err);
      }
    });
  }

  resetConfig(): void {
    if (confirm('Reset all settings to default values?')) {
      this.loadConfig();
    }
  }
}
