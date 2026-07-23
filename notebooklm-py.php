<?php
/**
 * Plugin Name: NotebookLM Py
 * Description: WordPress-hosted NotebookLM-py application.
 * Version: 2026.07.23.21
 * Author: GaijinWorld
 * Requires PHP: 8.0
 */

if (!defined('ABSPATH')) {
    exit;
}

add_action('template_redirect', function() {
    $request_uri = parse_url($_SERVER['REQUEST_URI'] ?? '', PHP_URL_PATH);
    if (rtrim($request_uri, '/') === '/notebooklm-py') {
        status_header(200);
        header('Content-Type: text/html; charset=UTF-8');
        header('Cache-Control: no-cache, no-store, must-revalidate');
        header('Pragma: no-cache');
        header('Expires: 0');
        readfile(__DIR__ . '/index.html');
        exit;
    }
}, 0);
