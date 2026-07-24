<?php
/**
 * Plugin Name: NotebookLM Py
 * Description: WordPress-hosted NotebookLM-py React 19 + Vite SPA Application.
 * Version: 2026.07.24.01
 * Author: GaijinWorld
 * Requires PHP: 8.1
 */

if (!defined('ABSPATH')) {
    exit;
}

define('NBLM_PLUGIN_VERSION', '2026.07.24.01');
define('NBLM_PLUGIN_FILE', __FILE__);
define('NBLM_PLUGIN_DIR', plugin_dir_path(__FILE__));
define('NBLM_PLUGIN_URL', plugin_dir_url(__FILE__));

final class NBLM_Plugin {
    private static ?NBLM_Plugin $instance = null;
    private ?array $vite_entry = null;
    private bool $vite_entry_loaded = false;

    public static function instance(): NBLM_Plugin {
        if (self::$instance === null) {
            self::$instance = new self();
        }
        return self::$instance;
    }

    private function __construct() {
        add_shortcode('notebooklm_py', [$this, 'render_shortcode']);
        add_action('template_redirect', [$this, 'maybe_render_shortcode_only_shell'], 0);
        add_action('rest_api_init', [$this, 'register_rest_routes']);
    }

    public function register_rest_routes(): void {
        register_rest_route('notebooklm-py/v1', '/start-server', [
            'methods' => 'POST',
            'callback' => [$this, 'handle_start_server'],
            'permission_callback' => '__return_true',
        ]);
    }

    public function handle_start_server(WP_REST_Request $request): WP_REST_Response {
        $params = json_decode((string)$request->get_body(), true) ?: [];
        $profile = $params['profile'] ?? 'default';
        $token = $params['token'] ?? 'mysecrettoken';

        // LocalWP PHP runs as SYSTEM — USERPROFILE is C:\Windows\system32.
        // Hardcode the actual user home; allow override via env for other setups.
        $user_home = getenv('NOTEBOOKLM_HOME_OVERRIDE') ?: 'C:\Users\jgoka';
        // Use RAW profile name — notebooklm Python does NOT sanitize the directory name
        $storage_file = $user_home . '\.notebooklm\profiles\\' . $profile . '\storage_state.json';
        $log_file = $user_home . '\.notebooklm\server-bridge.log';

        // Find Python executable — try common install paths, then fallback to PATH
        $python_exe = 'python';
        $candidates = ['C:\Python314\python.exe', 'C:\Python313\python.exe', 'C:\Python312\python.exe', 'C:\Python311\python.exe'];
        foreach ($candidates as $c) {
            if (file_exists($c)) {
                $python_exe = $c;
                break;
            }
        }

        // If no authenticated session exists, return auth_required — do NOT try
        // to run login --fresh in the background (it needs a Playwright browser window)
        if (!file_exists($storage_file)) {
            return new WP_REST_Response([
                'status' => 'auth_required',
                'profile' => $profile,
                'storage_exists' => false,
                'storage_path' => $storage_file,
                'python' => $python_exe,
                'message' => "No authenticated session for $profile. Run: $python_exe -m notebooklm --profile \"$profile\" login --browser msedge"
            ], 200);
        }

        if (strtoupper(substr(PHP_OS, 0, 3)) === 'WIN') {
            $cmd = sprintf(
                'start /b cmd /c "set NOTEBOOKLM_PROFILE=%s&& set NOTEBOOKLM_SERVER_TOKEN=%s&& %s -m notebooklm.server 2>"%s""',
                escapeshellarg($profile), escapeshellarg($token), escapeshellarg($python_exe), escapeshellarg($log_file)
            );
            pclose(popen($cmd, "r"));
        } else {
            $cmd = sprintf(
                'NOTEBOOKLM_PROFILE=%s NOTEBOOKLM_SERVER_TOKEN=%s %s -m notebooklm.server > /dev/null 2>%s &',
                escapeshellarg($profile), escapeshellarg($token), escapeshellarg($python_exe), escapeshellarg($log_file)
            );
            exec($cmd);
        }

        return new WP_REST_Response([
            'status' => 'started',
            'profile' => $profile,
            'token' => $token,
            'storage_exists' => true,
            'python' => $python_exe,
            'log_file' => $log_file,
            'message' => "notebooklm-server launched for $profile"
        ], 200);
    }

    public function render_shortcode(): string {
        return $this->get_app_root_markup();
    }

    private function get_vite_entry(): ?array {
        if ($this->vite_entry_loaded) {
            return $this->vite_entry;
        }
        $this->vite_entry_loaded = true;

        $manifest_path = NBLM_PLUGIN_DIR . 'dist/.vite/manifest.json';
        if (!is_readable($manifest_path)) {
            $manifest_path = NBLM_PLUGIN_DIR . 'web/dist/.vite/manifest.json';
        }
        if (!is_readable($manifest_path)) {
            return null;
        }

        $manifest = json_decode((string) file_get_contents($manifest_path), true);
        $entry = is_array($manifest)
            ? ($manifest['index.html'] ?? $manifest['web/index.html'] ?? null)
            : null;
        if (!is_array($entry) || empty($entry['file'])) {
            return null;
        }

        $js_file = ltrim((string) $entry['file'], '/');
        $css = [];
        foreach ((array) ($entry['css'] ?? []) as $css_file) {
            $css_file = ltrim((string) $css_file, '/');
            if ($css_file !== '') {
                $css[] = $css_file;
            }
        }

        $this->vite_entry = ['file' => $js_file, 'css' => $css];
        return $this->vite_entry;
    }

    private function get_runtime_config(): array {
        $request_scheme = is_ssl() ? 'https' : 'http';
        $http_host = $_SERVER['HTTP_HOST'] ?? 'gaijinworld-local.local';
        $base_url = $request_scheme . '://' . $http_host;

        return [
            'visibleVersion' => NBLM_PLUGIN_VERSION,
            'routeBase' => esc_url_raw($base_url . '/notebooklm-py/'),
            'siteOrigin' => esc_url_raw($base_url . '/'),
            'restBaseUrl' => esc_url_raw(rest_url('notebooklm-py/v1/')),
            'runtimeContractUrl' => esc_url_raw('/wp-content/plugins/notebooklm-py/runtime-contract.json'),
            'firebaseWebConfig' => [
                'apiKey' => 'AIzaSyAr5oe2DNaYQseh2iYPvBucZvibKyqNLOc',
                'authDomain' => 'gamified-network-engineer-app.firebaseapp.com',
                'projectId' => 'gamified-network-engineer-app',
                'storageBucket' => 'gamified-network-engineer-app.firebasestorage.app',
                'messagingSenderId' => '465331311664',
                'appId' => '1:465331311664:web:d558dfc8f83e81edcf89f5',
                'measurementId' => 'G-DCFM1RVPP5',
            ],
        ];
    }

    private function get_app_root_markup(): string {
        return '<div id="notebooklm-py-root"><div class="nblm-app-loading">Loading NotebookLM-py…</div></div>';
    }

    private function render_shell_asset_tags(): string {
        $entry = $this->get_vite_entry();
        $tags = [];

        if ($entry !== null) {
            foreach ($entry['css'] as $css_file) {
                $style_url = add_query_arg('ver', NBLM_PLUGIN_VERSION, '/wp-content/plugins/notebooklm-py/dist/' . $css_file);
                $tags[] = sprintf('<link rel="stylesheet" href="%s">', esc_url($style_url));
            }
        }

        $tags[] = sprintf(
            '<script>window.NBLM_RUNTIME_CONFIG = %s;</script>',
            wp_json_encode($this->get_runtime_config(), JSON_HEX_TAG | JSON_HEX_AMP | JSON_HEX_APOS | JSON_HEX_QUOT)
        );

        if ($entry !== null) {
            $tags[] = sprintf('<script type="module" src="%s"></script>', esc_url('/wp-content/plugins/notebooklm-py/dist/' . $entry['file']));
        }

        return implode('', $tags);
    }

    public function maybe_render_shortcode_only_shell(): void {
        if (is_admin() || wp_doing_ajax() || (defined('REST_REQUEST') && REST_REQUEST)) {
            return;
        }

        $request_uri = parse_url($_SERVER['REQUEST_URI'] ?? '', PHP_URL_PATH);
        if (rtrim($request_uri, '/') === '/notebooklm-py') {
            $this->render_shell();
        }
    }

    private function render_shell(): void {
        status_header(200);
        nocache_headers();

        $title = 'NotebookLM-py App v' . NBLM_PLUGIN_VERSION . ' Live';
        $app_markup = $this->get_app_root_markup();
        $asset_tags = $this->render_shell_asset_tags();

        echo '<!doctype html>';
        echo '<html ' . get_language_attributes() . '>';
        echo '<head>';
        echo '<meta charset="' . esc_attr(get_bloginfo('charset')) . '">';
        echo '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">';
        echo '<title>' . esc_html($title) . '</title>';
        echo '<link rel="preconnect" href="https://fonts.googleapis.com">';
        echo '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>';
        echo '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap" rel="stylesheet">';
        echo '<style>';
        echo 'html,body{margin:0;padding:0;height:100%;background:#0d1117;}';
        echo 'body{overflow:hidden;font-family:Inter,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#e6edf3;}';
        echo '#notebooklm-py-root{width:100vw;height:100vh;min-height:100vh;}';
        echo '@supports (height:100dvh){#notebooklm-py-root{height:100dvh;min-height:100dvh;}}';
        echo '.nblm-build-error{margin:32px auto;max-width:720px;padding:16px 20px;border:1px solid #ef4444;border-radius:12px;background:#fef2f2;color:#991b1b;}';
        echo '.nblm-app-loading{display:flex;align-items:center;justify-content:center;height:100%;font-size:18px;color:#64748b;}';
        echo '</style>';
        echo $asset_tags;
        echo '</head>';
        echo '<body class="notebooklm-py-shell">';
        echo $app_markup;
        echo '</body>';
        echo '</html>';
        exit;
    }
}

NBLM_Plugin::instance();
