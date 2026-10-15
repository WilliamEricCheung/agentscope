# Agent configuration for robustness evaluation
{ pkgs ? import <nixpkgs> {} }:

{
  # Agent core settings
  agent = {
    name = "multi-round-planning-agent";
    version = "1.0.0";
    
    # Planning parameters
    planning = {
      maxSteps = 50;
      timeoutPerStep = 30;  # seconds
      retryAttempts = 3;
      backoffMultiplier = 2.0;
    };
    
    # Tool usage configuration
    tools = {
      # Web browsing tools
      browser = {
        enabled = true;
        headless = true;
        timeout = 30;
        userAgent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36";
      };
      
      # API tools
      api = {
        enabled = true;
        rateLimit = 10;  # requests per second
        timeout = 60;
      };
      
      # File system tools
      filesystem = {
        enabled = true;
        readOnly = false;
        allowedPaths = [ "/tmp" "./workspace" ];
      };
    };
    
    # Error handling and recovery
    errorHandling = {
      enableRetry = true;
      enableFallback = true;
      logErrors = true;
      captureScreenshots = true;
    };
  };
  
  # Environment-specific overrides
  environments = {
    development = {
      agent.planning.maxSteps = 100;
      agent.planning.timeoutPerStep = 60;
      agent.tools.browser.headless = false;
    };
    
    testing = {
      agent.planning.maxSteps = 25;
      agent.planning.timeoutPerStep = 15;
      agent.tools.browser.headless = true;
    };
    
    production = {
      agent.planning.maxSteps = 50;
      agent.planning.timeoutPerStep = 30;
      agent.tools.browser.headless = true;
      agent.errorHandling.captureScreenshots = false;
    };
  };
}