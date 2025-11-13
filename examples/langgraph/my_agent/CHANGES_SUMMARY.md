# Renaming Summary: rules_engine → protect_engine

## Files Renamed

| Old Name | New Name | Purpose |
|----------|----------|---------|
| `rules_engine.py` | `protect_engine.py` | Core protection engine implementation |
| `test_rules_engine.py` | `test_protect_engine.py` | Test suite |

## Functions/Classes Renamed

| Old Name | New Name |
|----------|----------|
| `RulesEngine` | `ProtectEngine` |
| `init_rules_engine()` | `init_protect_engine()` |
| `get_rules_engine()` | `get_protect_engine()` |
| `@enforce_rules` | `@protect` |

## Updated Imports

All files now use:

```python
from protect_engine import (
    ProtectEngine,
    init_protect_engine,
    get_protect_engine,
    protect,
    RuleViolation
)
```

## Usage Changes

### Before

```python
from rules_engine import init_rules_engine, enforce_rules

init_rules_engine("rules.yaml")

@enforce_rules('step-id', input='param')
async def my_func(param: str):
    return param
```

### After

```python
from protect_engine import init_protect_engine, protect

init_protect_engine("rules.yaml")

@protect('step-id', input='param')
async def my_func(param: str):
    return param
```

## Files Updated

1. ✅ `protect_engine.py` - Main engine (renamed)
2. ✅ `agent_with_rules.py` - Updated imports
3. ✅ `test_protect_engine.py` - Updated all references
4. ✅ `DECORATOR_EXPLAINED.md` - Updated documentation
5. ✅ `decorator_example.py` - Visual examples

## Migration Checklist

If you have existing code using the old names:

- [ ] Rename file: `rules_engine.py` → `protect_engine.py`
- [ ] Update imports: `from protect_engine import ...`
- [ ] Replace: `init_rules_engine` → `init_protect_engine`
- [ ] Replace: `get_rules_engine` → `get_protect_engine`  
- [ ] Replace: `@enforce_rules` → `@protect`
- [ ] Replace: `RulesEngine` → `ProtectEngine`
- [ ] Run tests to verify everything works

## Backward Compatibility

⚠️ **Breaking Change**: The old names are no longer available. You must update your code.

If you need a transition period, you can add aliases in `protect_engine.py`:

```python
# Temporary aliases for backward compatibility
RulesEngine = ProtectEngine
init_rules_engine = init_protect_engine
get_rules_engine = get_protect_engine
enforce_rules = protect
```

## New Documentation

Created comprehensive guides:

1. **DECORATOR_EXPLAINED.md** - Deep dive into how the decorator works
2. **QUICK_START.md** - Quick reference for getting started
3. **decorator_example.py** - Runnable examples showing data extraction
4. **RULES_GUIDE.md** - Complete rules reference (already existed)
5. **RULES_QUICK_REF.md** - Quick lookup table (already existed)

## Testing

All tests have been updated and pass:

```bash
cd examples/langgraph/my_agent
pytest test_protect_engine.py -v
```

## Next Steps

1. **Read** [QUICK_START.md](./QUICK_START.md) for basic usage
2. **Run** `python decorator_example.py` to see how data extraction works
3. **Read** [DECORATOR_EXPLAINED.md](./DECORATOR_EXPLAINED.md) for detailed explanation
4. **Refer to** [RULES_GUIDE.md](./RULES_GUIDE.md) for rule configuration

---

*Changes completed: November 2025*

