@echo off
python test_scraping_rules_modifications.py > test_results.txt 2>&1
type test_results.txt
