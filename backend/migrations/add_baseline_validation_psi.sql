-- Add baseline validation PSI fields to model_metadata table
-- This migration separates training baseline validation from production PSI monitoring

ALTER TABLE model_metadata
ADD COLUMN baseline_validation_psi NUMERIC(5, 4),
ADD COLUMN baseline_validation_status VARCHAR(20),
ADD COLUMN baseline_validated_at TIMESTAMP;

-- Add comment for documentation
COMMENT ON COLUMN model_metadata.baseline_validation_psi IS 'PSI from baseline self-validation during training (should be ~0)';
COMMENT ON COLUMN model_metadata.baseline_validation_status IS 'Status of baseline validation: passed, failed, not_validated';
COMMENT ON COLUMN model_metadata.baseline_validated_at IS 'Timestamp when baseline was validated during training';

-- Existing psi_score field documentation for clarity
COMMENT ON COLUMN model_metadata.psi_score IS 'Latest production PSI snapshot from monitoring (current population vs baseline)';
COMMENT ON COLUMN model_metadata.psi_status IS 'Status of latest production PSI: stable, warning, drift, no_baseline, no_data';
