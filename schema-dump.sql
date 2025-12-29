-- Schema inspection queries for Supabase (run in SQL editor)

-- 1) Tables
select table_schema, table_name
from information_schema.tables
where table_schema = 'public' and table_type = 'BASE TABLE'
order by table_name;

-- 2) Columns + defaults
select table_name, ordinal_position, column_name, data_type, is_nullable, column_default
from information_schema.columns
where table_schema = 'public'
order by table_name, ordinal_position;

-- 3) Constraints (PK/FK/UNIQUE/CHECK)
select
  tc.table_name,
  tc.constraint_type,
  tc.constraint_name,
  kcu.column_name,
  ccu.table_name as foreign_table_name,
  ccu.column_name as foreign_column_name
from information_schema.table_constraints tc
left join information_schema.key_column_usage kcu
  on tc.constraint_name = kcu.constraint_name and tc.table_schema = kcu.table_schema
left join information_schema.constraint_column_usage ccu
  on tc.constraint_name = ccu.constraint_name and tc.table_schema = ccu.table_schema
where tc.table_schema = 'public'
order by tc.table_name, tc.constraint_name, kcu.ordinal_position;

-- 4) Indexes
select tablename, indexname, indexdef
from pg_indexes
where schemaname = 'public'
order by tablename, indexname;

-- 5) Views
select table_name, view_definition
from information_schema.views
where table_schema = 'public'
order by table_name;

-- 6) Functions (definitions)
select p.proname, pg_get_functiondef(p.oid) as definition
from pg_proc p
join pg_namespace n on p.pronamespace = n.oid
where n.nspname = 'public'
order by p.proname;

-- 7) Triggers
select event_object_table, trigger_name, action_statement
from information_schema.triggers
where trigger_schema = 'public'
order by event_object_table, trigger_name;
