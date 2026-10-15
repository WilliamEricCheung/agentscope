# Tool environments configuration for robustness testing
{ pkgs ? import <nixpkgs> {} }:

let
  # Common tool definitions
  commonTools = {
    # Web browsing and scraping tools
    webBrowser = {
      name = "web-browser";
      type = "browser";
      capabilities = [ "navigation" "interaction" "screenshot" "pdf-export" ];
      dependencies = with pkgs; [ firefox-esr chromium ];
    };
    
    # HTTP client tools
    httpClient = {
      name = "http-client";
      type = "api";
      capabilities = [ "get" "post" "put" "delete" "headers" "cookies" ];
      dependencies = with pkgs.python311Packages; [ requests urllib3 ];
    };
    
    # File system tools
    fileSystem = {
      name = "file-system";
      type = "local";
      capabilities = [ "read" "write" "list" "create-dir" "delete" ];
      dependencies = with pkgs; [ coreutils findutils ];
    };
    
    # JSON processing tools
    jsonProcessor = {
      name = "json-processor";
      type = "data";
      capabilities = [ "parse" "transform" "validate" "query" ];
      dependencies = with pkgs; [ jq python311Packages.jsonschema ];
    };
  };
  
  # Environment-specific tool configurations
  environments = {
    # Basic environment with essential tools
    basic = {
      tools = [
        commonTools.webBrowser
        commonTools.httpClient
        commonTools.fileSystem
      ];
      constraints = {
        maxConcurrentTools = 3;
        memoryLimit = "512M";
        cpuLimit = "1.0";
      };
    };
    
    # Extended environment with additional capabilities
    extended = {
      tools = [
        commonTools.webBrowser
        commonTools.httpClient
        commonTools.fileSystem
        commonTools.jsonProcessor
        {
          name = "shell-executor";
          type = "system";
          capabilities = [ "execute" "pipe" "redirect" ];
          dependencies = with pkgs; [ bash coreutils ];
        }
        {
          name = "database-client";
          type = "database";
          capabilities = [ "query" "insert" "update" "delete" ];
          dependencies = with pkgs; [ sqlite postgresql ];
        }
      ];
      constraints = {
        maxConcurrentTools = 8;
        memoryLimit = "2G";
        cpuLimit = "4.0";
      };
    };
    
    # Minimal environment for stress testing
    minimal = {
      tools = [
        commonTools.httpClient
        commonTools.fileSystem
      ];
      constraints = {
        maxConcurrentTools = 2;
        memoryLimit = "128M";
        cpuLimit = "0.5";
      };
    };
    
    # Full environment with all available tools
    full = {
      tools = [
        commonTools.webBrowser
        commonTools.httpClient
        commonTools.fileSystem
        commonTools.jsonProcessor
        {
          name = "shell-executor";
          type = "system";
          capabilities = [ "execute" "pipe" "redirect" "background" ];
          dependencies = with pkgs; [ bash coreutils gnumake ];
        }
        {
          name = "database-client";
          type = "database";
          capabilities = [ "query" "insert" "update" "delete" "transaction" ];
          dependencies = with pkgs; [ sqlite postgresql mysql80 ];
        }
        {
          name = "image-processor";
          type = "media";
          capabilities = [ "resize" "crop" "format-convert" "metadata" ];
          dependencies = with pkgs; [ imagemagick python311Packages.pillow ];
        }
        {
          name = "network-tools";
          type = "network";
          capabilities = [ "ping" "traceroute" "dns-lookup" "port-scan" ];
          dependencies = with pkgs; [ iputils netcat bind ];
        }
      ];
      constraints = {
        maxConcurrentTools = 16;
        memoryLimit = "8G";
        cpuLimit = "8.0";
      };
    };
  };

in
{
  inherit commonTools environments;
  
  # Default environment for testing
  defaultEnvironment = environments.extended;
  
  # Helper function to get environment by name
  getEnvironment = name: environments.${name} or environments.basic;
}