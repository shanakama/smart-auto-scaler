import { Injectable } from "@angular/core";
import { HttpClient, HttpHeaders } from "@angular/common/http";
import { Observable, throwError } from "rxjs";
import { catchError } from "rxjs/operators";
import {
  Pod,
  PodMetrics,
  PodResources,
  ScalingDecision,
  Statistics,
  Config,
  AutoscaleStatus,
  HealthStatus,
} from "../models/api.models";

@Injectable({
  providedIn: "root",
})
export class ApiService {
  private apiUrl = "http://localhost:5404";

  private httpOptions = {
    headers: new HttpHeaders({
      "Content-Type": "application/json",
    }),
  };

  constructor(private http: HttpClient) {}

  // Health Check
  getHealth(): Observable<HealthStatus> {
    return this.http
      .get<HealthStatus>(`${this.apiUrl}/health`)
      .pipe(catchError(this.handleError));
  }

  // Configuration
  getConfig(): Observable<Config> {
    return this.http
      .get<Config>(`${this.apiUrl}/config`)
      .pipe(catchError(this.handleError));
  }

  updateConfig(config: Partial<Config>): Observable<any> {
    return this.http
      .post(`${this.apiUrl}/config`, config, this.httpOptions)
      .pipe(catchError(this.handleError));
  }

  // Pods
  getPods(): Observable<{ success: boolean; count: number; pods: Pod[] }> {
    return this.http
      .get<any>(`${this.apiUrl}/pods`)
      .pipe(catchError(this.handleError));
  }

  getPodInfo(
    namespace: string,
    podName: string
  ): Observable<{
    success: boolean;
    pod: string;
    metrics: PodMetrics;
    resources: PodResources;
  }> {
    return this.http
      .get<any>(`${this.apiUrl}/pods/${namespace}/${podName}`)
      .pipe(catchError(this.handleError));
  }

  // Scaling Actions
  scalePod(
    namespace: string,
    podName: string
  ): Observable<{
    success: boolean;
    result: ScalingDecision;
  }> {
    return this.http
      .post<any>(`${this.apiUrl}/scale/pod/${namespace}/${podName}`, {})
      .pipe(catchError(this.handleError));
  }

  scaleAllPods(): Observable<{
    success: boolean;
    processed: number;
    results: ScalingDecision[];
    statistics: Statistics;
    timestamp: string;
  }> {
    return this.http
      .post<any>(`${this.apiUrl}/scale/all`, {})
      .pipe(catchError(this.handleError));
  }

  // Decisions
  getDecisions(limit: number = 50): Observable<{
    success: boolean;
    count: number;
    decisions: ScalingDecision[];
  }> {
    return this.http
      .get<any>(`${this.apiUrl}/decisions?limit=${limit}`)
      .pipe(catchError(this.handleError));
  }

  // Statistics
  getStatistics(): Observable<{ success: boolean; statistics: Statistics }> {
    return this.http
      .get<any>(`${this.apiUrl}/statistics`)
      .pipe(catchError(this.handleError));
  }

  // Auto-scaling
  startAutoscale(): Observable<{
    success: boolean;
    message: string;
    interval: number;
  }> {
    return this.http
      .post<any>(`${this.apiUrl}/autoscale/start`, {})
      .pipe(catchError(this.handleError));
  }

  stopAutoscale(): Observable<{ success: boolean; message: string }> {
    return this.http
      .post<any>(`${this.apiUrl}/autoscale/stop`, {})
      .pipe(catchError(this.handleError));
  }

  getAutoscaleStatus(): Observable<AutoscaleStatus> {
    return this.http
      .get<AutoscaleStatus>(`${this.apiUrl}/autoscale/status`)
      .pipe(catchError(this.handleError));
  }

  // Model Info
  getModelInfo(): Observable<any> {
    return this.http
      .get(`${this.apiUrl}/model/info`)
      .pipe(catchError(this.handleError));
  }

  // Error Handler
  private handleError(error: any) {
    let errorMessage = "An error occurred";

    if (error.error instanceof ErrorEvent) {
      // Client-side error
      errorMessage = `Error: ${error.error.message}`;
    } else {
      // Server-side error
      errorMessage = `Error Code: ${error.status}\nMessage: ${error.message}`;
    }

    console.error(errorMessage);
    return throwError(() => new Error(errorMessage));
  }
}
