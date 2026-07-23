<?php
$port = 10005;
echo "Connecting to MySQL on 127.0.0.1:$port...\n";
$mysqli = new mysqli('127.0.0.1', 'root', 'root', 'local', $port);
if ($mysqli->connect_error) {
    die("Connection failed: " . $mysqli->connect_error . "\n");
}
echo "Connected successfully to MySQL!\n";

$res = $mysqli->query("SELECT option_value FROM wp_options WHERE option_name = 'active_plugins'");
if ($res && $row = $res->fetch_assoc()) {
    $plugins = unserialize($row['option_value']);
    echo "Current Active Plugins:\n";
    print_r($plugins);

    if (!in_array('notebooklm-py/notebooklm-py.php', $plugins)) {
        $plugins[] = 'notebooklm-py/notebooklm-py.php';
        $new_val = serialize(array_values(array_unique($plugins)));
        $stmt = $mysqli->prepare("UPDATE wp_options SET option_value = ? WHERE option_name = 'active_plugins'");
        $stmt->bind_param('s', $new_val);
        $stmt->execute();
        echo "\n--> ACTIVATED notebooklm-py/notebooklm-py.php IN WORDPRESS DB!\n";
    } else {
        echo "\nnotebooklm-py/notebooklm-py.php IS ALREADY ACTIVE IN WORDPRESS DB.\n";
    }
}
