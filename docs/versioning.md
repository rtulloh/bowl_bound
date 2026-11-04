# Version information

The current release candidate is **0.1.0-alpha.5**. Python packaging uses the equivalent
PEP 440 form **0.1.0a5**. Its planned immutable Git tag is `v0.1.0-alpha.5`.

`bowl_bound.__version__`, project metadata and API OpenAPI metadata use the
Python form. Frontend package/lock metadata and `bowl_bound.DISPLAY_VERSION`
use the public form. `GET /api/version` returns both as `version` and
`python_version`, without filesystem paths or machine details. For a local
default server, open <http://127.0.0.1:8000/api/version>. Include `version`
when reporting a problem. Standalone launcher version reporting will use the
same public identity.

Application version numbers are not save compatibility profiles. Milestone 33 uses
the `bowl-bound-m33-v1` engine profile with the existing save schema. The Alpha 5
version metadata does not change either compatibility identifier. Alpha releases
may still have known limitations; keep copies of saves before upgrading. Never
delete/reuse an already published tag.
