# Robustness tests configuration for NixOS Agent Environment

{ pkgs ? import <nixpkgs> {} }:

let
  # Test scenarios for robustness evaluation
  testScenarios = {
    # Tool availability tests
    toolAvailability = {
      description = "Test agent's ability to detect and use available tools";
      environments = [ "basic" "extended" "minimal" "full" ];
      expectedTools = {
        basic = [ "web-browser" "http-client" "file-system" ];
        extended = [ "web-browser" "http-client" "file-system" "json-processor" "shell-executor" "database-client" ];
        minimal = [ "http-client" "file-system" ];
        full = [ "web-browser" "http-client" "file-system" "json-processor" "shell-executor" "database-client" "image-processor" "network-tools" ];
      };
    };
    
    # Error recovery tests
    errorRecovery = {
      description = "Test agent's ability to recover from tool failures";
      failureTypes = [ "timeout" "connection-error" "permission-denied" "invalid-input" ];
      retryStrategies = [ "exponential-backoff" "fixed-delay" "immediate" ];
      maxRetries = 3;
    };
    
    # Performance stability tests
    performanceStability = {
      description = "Test agent's performance under various load conditions";
      loadLevels = [ "low" "medium" "high" "extreme" ];
      concurrentAgents = [ 1 5 10 20 ];
      timeoutThresholds = {
        low = 30;
        medium = 60;
        high = 120;
        extreme = 300;
      };
    };
    
    # Version compatibility tests
    versionCompatibility = {
      description = "Test agent's compatibility with different tool versions";
      pythonVersions = [ "3.9" "3.10" "3.11" "3.12" ];
      browserVersions = {
        chrome = [ "118" "119" "120" ];
        firefox = [ "115" "116" "117" ];
      };
      apiVersions = [ "v1" "v2" "latest" ];
    };
  };
  
  # Test metrics and thresholds
  testMetrics = {
    successRate = {
      threshold = 0.95;  # 95% success rate required
      weight = 0.4;
    };
    
    averageCompletionTime = {
      threshold = 120;   # 120 seconds maximum average time
      weight = 0.3;
    };
    
    errorRecoveryRate = {
      threshold = 0.85;  # 85% error recovery rate required
      weight = 0.2;
    };
    
    resourceUtilization = {
      cpuThreshold = 0.8;   # 80% CPU utilization maximum
      memoryThreshold = 0.7; # 70% memory utilization maximum
      weight = 0.1;
    };
  };

in
{
  inherit testScenarios testMetrics;
  
  # Overall robustness score calculation
  calculateRobustnessScore = metrics: 
    let
      successScore = if metrics.successRate >= testMetrics.successRate.threshold then 1.0 else metrics.successRate / testMetrics.successRate.threshold;
      timeScore = if metrics.averageCompletionTime <= testMetrics.averageCompletionTime.threshold then 1.0 else testMetrics.averageCompletionTime.threshold / metrics.averageCompletionTime;
      recoveryScore = if metrics.errorRecoveryRate >= testMetrics.errorRecoveryRate.threshold then 1.0 else metrics.errorRecoveryRate / testMetrics.errorRecoveryRate.threshold;
      resourceScore = let
        cpuScore = if metrics.cpuUtilization <= testMetrics.resourceUtilization.cpuThreshold then 1.0 else testMetrics.resourceUtilization.cpuThreshold / metrics.cpuUtilization;
        memoryScore = if metrics.memoryUtilization <= testMetrics.resourceUtilization.memoryThreshold then 1.0 else testMetrics.resourceUtilization.memoryThreshold / metrics.memoryUtilization;
      in (cpuScore + memoryScore) / 2.0;
    in
    (successScore * testMetrics.successRate.weight) +
    (timeScore * testMetrics.averageCompletionTime.weight) +
    (recoveryScore * testMetrics.errorRecoveryRate.weight) +
    (resourceScore * testMetrics.resourceUtilization.weight);
}