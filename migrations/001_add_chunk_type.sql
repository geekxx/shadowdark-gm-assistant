-- Add chunk_type column to chunk table for intelligent content classification
-- Run this migration after updating the codebase

ALTER TABLE chunk ADD COLUMN IF NOT EXISTS chunk_type VARCHAR;

-- Optional: Update existing chunks to classify their content
-- This will scan existing chunks and apply intelligent classification
-- You can run this after the column is added:
-- UPDATE chunk SET chunk_type = 'rule' WHERE chunk_type IS NULL;  -- Add your classification logic here

COMMENT ON COLUMN chunk.chunk_type IS 'Content-based classification (monster, spell, rule, table, etc.) independent of parent document type';