-- Add PSI status and timestamp fields to model_metadata table
-- Run this manually to update the database schema

ALTER TABLE model_metadata
ADD COLUMN IF NOT EXISTS psi_status VARCHAR(20),
ADD COLUMN IF NOT EXISTS psi_calculated_at TIMESTAMP WITH TIME ZONE;

COMMENT ON COLUMN model_metadata.psi_status IS 'PSI stability status: stable, warning, drift, no_baseline, no_data';
COMMENT ON COLUMN model_metadata.psi_calculated_at IS 'Timestamp when PSI score was last calculated';
