<?php
$mysqli = new mysqli('127.0.0.1', 'root', 'root', 'local', 10005);
$res = $mysqli->query("SELECT option_name, option_value FROM wp_options WHERE option_name IN ('siteurl', 'home')");
while ($row = $res->fetch_assoc()) {
    echo $row['option_name'] . ' => ' . $row['option_value'] . "\n";
}
