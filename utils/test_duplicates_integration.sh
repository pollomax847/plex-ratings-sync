# Test de l'intégration des doublons dans le workflow mensuel
echo '=== Test analyse doublons ==='
if [ -f 'duplicate_detector.py' ]; then
    echo '✅ Script duplicate_detector.py trouvé'
    sudo python3 duplicate_detector.py > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo '✅ Analyse doublons exécutée avec succès'
        LATEST=$(ls -t duplicate_analysis_*.json 2>/dev/null | head -1)
        if [ -n "$LATEST" ]; then
            echo "📄 Dernier rapport: $LATEST"
            if command -v jq &> /dev/null; then
                STATS=$(jq -r '.statistics | "Doublons exacts: \(.total_exact_duplicate_groups), Similaires: \(.total_similar_groups), Fichiers: \(.total_file_duplicate_groups)"' "$LATEST" 2>/dev/null)
                echo "📊 $STATS"
            fi
        fi
    else
        echo '❌ Erreur lors de l analyse'
    fi
else
    echo '❌ Script duplicate_detector.py non trouvé'
fi
