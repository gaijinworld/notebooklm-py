<?php
define('WP_USE_THEMES', false);
require_once 'C:/Users/jgoka/Local Sites/gaijinworld-local/app/public/wp-load.php';
$plugins = get_option('active_plugins');
echo "Active Plugins:\n";
print_r($plugins);

// Check if notebooklm-py is active
$is_active = in_array('notebooklm-py/notebooklm-py.php', $plugins);
echo "\nIs notebooklm-py active? " . ($is_active ? "YES" : "NO") . "\n";

if (!$is_active) {
    $plugins[] = 'notebooklm-py/notebooklm-py.php';
    update_option('active_plugins', array_values(array_unique($plugins)));
    echo "ACTIVATED notebooklm-py/notebooklm-py.php in WordPress!\n";
}
