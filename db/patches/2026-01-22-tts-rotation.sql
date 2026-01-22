CREATE TABLE IF NOT EXISTS tts_rotation (
  id INTEGER PRIMARY KEY DEFAULT 1,
  counter INTEGER NOT NULL DEFAULT 0,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

INSERT INTO tts_rotation (id, counter)
VALUES (1, 0)
ON CONFLICT (id) DO NOTHING;

CREATE OR REPLACE FUNCTION next_tts_combo(p_mod INTEGER DEFAULT 9)
RETURNS INTEGER AS $$
DECLARE current_val INTEGER;
BEGIN
  INSERT INTO tts_rotation (id, counter)
  VALUES (1, 0)
  ON CONFLICT (id) DO NOTHING;

  SELECT counter INTO current_val
  FROM tts_rotation
  WHERE id = 1
  FOR UPDATE;

  UPDATE tts_rotation
  SET counter = counter + 1,
      updated_at = NOW()
  WHERE id = 1;

  RETURN MOD(current_val, p_mod);
END;
$$ LANGUAGE plpgsql;
