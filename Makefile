.PHONY: check-yaml
check-yaml:
	@python3 scripts/validate_yaml.py

.PHONY: help
help:
	@echo "Available targets:"
	@echo "  check-yaml    - Validate YAML syntax in workflow files"
	@echo "  help          - Show this help message"
