# TDD Log

## TASK-427 — GREEN (End)

**Time:** 2026-05-19
**Status:** Tests Passing
**Details:**
```
tests/test_task_427.py::test_allocation_item_validation PASSED
tests/test_task_427.py::test_strategy_request_with_allocation PASSED
tests/test_task_427.py::test_strategy_request_allocation_sum_validation PASSED
tests/test_task_427.py::test_strategy_request_allocation_optional PASSED
tests/test_task_427.py::test_strategy_request_cannot_have_both_symbols_and_allocation PASSED
tests/test_task_427.py::test_allocation_item_symbol_format PASSED
tests/test_task_427.py::test_allocation_empty_is_valid PASSED
tests/test_task_427.py::test_allocation_unique_symbols PASSED
8 passed in 0.58s
```
- Added `AllocationItem` model to backend schemas with validation
- Added `allocation` field to `StrategyRequest` with sum-to-100% validation
- Implemented frontend multi-crypto allocation UI with sliders
- Added `useAllocation` signal to toggle between AI auto-selection and manual allocation
- Frontend validates allocation sum and disables submit if invalid


## TASK-015 — RED (Start)

**Time:** 2026-05-15 12:05:48  
**Status:** Tests Failing  
**Details:**
```
E
======================================================================
ERROR: test_pipeline_metrics (unittest.loader._FailedTest.test_pipeline_metrics)
----------------------------------------------------------------------
ImportError: Failed to import test module: test_pipeline_metrics
Traceback (most recent call last):
  File "C:\Python312\Lib\unittest\loader.py", line 396, in _find_test_path
    module = self._get_module_from_name(name)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "
```


## TASK-033 — GREEN (End)

**Time:** 2026-05-15 15:30:00 (approx)
**Status:** Tests Passing
**Details:**
```
tests\test_task_033.py ..                                                        [100%]
tests\test_pipeline_metrics.py .                                                 [100%]
```
- Implemented `get_db` dependency in `app/dependencies.py`.
- Fixed `_DummyTable` to support `.single()` method in both root stub and `app/db/supabase_client.py`.
- Fixed `test_pipeline_metrics.py` import and expectation for custom exception handler.

## TASK-035 — RED (Start)

**Time:** 2026-05-15 12:53:44  
**Status:** Tests Failing  
**Details:**
```
E
======================================================================
ERROR: test_pipeline_metrics (unittest.loader._FailedTest.test_pipeline_metrics)
----------------------------------------------------------------------
ImportError: Failed to import test module: test_pipeline_metrics
Traceback (most recent call last):
  File "C:\Python312\Lib\unittest\loader.py", line 396, in _find_test_path
    module = self._get_module_from_name(name)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "
```


## TASK-035 — COMPLETE (Failed)

**Time:** 2026-05-15 14:18:47  
**Status:** Tests Still Failing  
**Details:**
```
EE
======================================================================
ERROR: test_pipeline_metrics (unittest.loader._FailedTest.test_pipeline_metrics)
----------------------------------------------------------------------
ImportError: Failed to import test module: test_pipeline_metrics
Traceback (most recent call last):
  File "C:\Python312\Lib\unittest\loader.py", line 396, in _find_test_path
    module = self._get_module_from_name(name)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File 
```


## TASK-038 — GREEN (OhlcvRepository)

**Time:** 2026-05-15 14:55:00
**Status:** Tests Passing
**Details:**
- Implementato `OhlcvRepository` per gestione cache OHLCV.
- Dependency injection `get_ohlcv_repo` configurata.
- Test unitari verificati con successo.


## TASK-038 — COMPLETE (Failed)

**Time:** 2026-05-15 16:22:57  
**Status:** Tests Still Failing  
**Details:**
```
Traceback (most recent call last):
  File "<frozen runpy>", line 198, in _run_module_as_main
  File "<frozen runpy>", line 88, in _run_code
  File "C:\Python312\Lib\unittest\__main__.py", line 18, in <module>
    main(module=None)
  File "C:\Python312\Lib\unittest\main.py", line 104, in __init__
    self.parseArgs(argv)
  File "C:\Python312\Lib\unittest\main.py", line 130, in parseArgs
    self._do_discovery(argv[2:])
  File "C:\Python312\Lib\unittest\main.py", line 253, in _do_discovery
    sel
```


## TASK-041 — RED (Start)

**Time:** 2026-05-15 16:39:56  
**Status:** Tests Failing  
**Details:**
```

----------------------------------------------------------------------
Ran 0 tests in 0.000s

NO TESTS RAN

```


## TASK-068 — RED (Start)

**Time:** 2026-05-15 16:46:12  
**Status:** Tests Failing  
**Details:**
```

----------------------------------------------------------------------
Ran 0 tests in 0.000s

NO TESTS RAN

```


## TASK-069 — RED (Start)

**Time:** 2026-05-15 16:57:42  
**Status:** Tests Failing  
**Details:**
```

----------------------------------------------------------------------
Ran 0 tests in 0.000s

NO TESTS RAN

```


## TASK-070 — RED (Start)

**Time:** 2026-05-15 17:42:03  
**Status:** Tests Failing  
**Details:**
```

----------------------------------------------------------------------
Ran 0 tests in 0.000s

NO TESTS RAN

```


## TASK-209 — RED (Start)

**Time:** 2026-05-18 15:00:17  
**Status:** Tests Failing  
**Details:**
```

----------------------------------------------------------------------
Ran 0 tests in 0.000s

NO TESTS RAN

```


## TASK-209 — COMPLETE (Failed)

**Time:** 2026-05-18 15:20:04  
**Status:** Tests Still Failing  
**Details:**
```

----------------------------------------------------------------------
Ran 0 tests in 0.000s

NO TESTS RAN

```


## TASK-209 — GREEN (Complete)

**Time:** 2026-05-18 15:25:29  
**Status:** All Tests Passing  
**Details:**
```
============================= test session starts =============================
platform win32 -- Python 3.12.6, pytest-8.3.3, pluggy-1.6.0 -- C:\Python312\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\andrea.mazzarotto\myJobs\SynthTrade\synthtrade\backend
configfile: pytest.ini
plugins: anyio-4.13.0, asyncio-0.24.0, cov-7.1.0, mock-3.14.0
asyncio: mode=Mode.AUTO, default_loop_scope=function
collecting ... collected 296 items

synthtrade\backend\test_task_041.py::test_ranker_high_risk_pre
```


## TASK-214 — RED (Start)

**Time:** 2026-05-18 16:03:45  
**Status:** Tests Failing  
**Details:**
```
============================= test session starts =============================
platform win32 -- Python 3.12.6, pytest-8.3.3, pluggy-1.6.0 -- C:\Python312\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\andrea.mazzarotto\myJobs\SynthTrade
plugins: anyio-4.13.0, asyncio-0.24.0, cov-7.1.0, mock-3.14.0
asyncio: mode=Mode.STRICT, default_loop_scope=None
collecting ... collected 1 item

tests/test_task_214.py::test_task_214_placeholder FAILED                 [100%]

============================
```


## TASK-214 — GREEN (Complete)

**Time:** 2026-05-18 16:36:18  
**Status:** All Tests Passing  
**Details:**
```
============================= test session starts =============================
platform win32 -- Python 3.12.6, pytest-8.3.3, pluggy-1.6.0 -- C:\Python312\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\andrea.mazzarotto\myJobs\SynthTrade
plugins: anyio-4.13.0, asyncio-0.24.0, cov-7.1.0, mock-3.14.0
asyncio: mode=Mode.STRICT, default_loop_scope=None
collecting ... collected 4 items

tests/test_task_214.py::test_registry_singleton PASSED                   [ 25%]
tests/test_task_214.py::test
```


## TASK-418 — RED (Start)

**Time:** 2026-05-18 16:51:19  
**Status:** Tests Failing  
**Details:**
```
============================= test session starts =============================
platform win32 -- Python 3.12.6, pytest-8.3.3, pluggy-1.6.0 -- C:\Python312\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\andrea.mazzarotto\myJobs\SynthTrade
plugins: anyio-4.13.0, asyncio-0.24.0, cov-7.1.0, mock-3.14.0
asyncio: mode=Mode.STRICT, default_loop_scope=None
collecting ... collected 1 item

tests/test_task_418.py::test_task_418_placeholder FAILED                 [100%]

============================
```

