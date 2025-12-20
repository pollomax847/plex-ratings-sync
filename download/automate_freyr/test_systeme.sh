# Test rapide du système Freyr
echo '=== Test de connectivité ==='
ping -4 -c 1 google.com > /dev/null && echo '✅ Internet OK' || echo '❌ Internet KO'

echo '=== Test freyr ==='
~/bin/freyr-mybook-fixed --version | head -1

echo '=== Test surveillance ==='
./surveille_auto_deezer.sh | tail -3

echo '=== État des caches ==='
ls -la ~/.*deezer_cache_* | wc -l
echo 'caches trouvés'

