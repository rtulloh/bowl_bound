# Version information

The current prerelease is **0.1.0-alpha.3**. Python packaging uses the equivalent
PEP 440 form **0.1.0a3**. Its immutable Git tag is `v0.1.0-alpha.3`.

`bowl_bound.__version__`, project metadata and API OpenAPI metadata use the
Python form. Frontend package/lock metadata and `bowl_bound.DISPLAY_VERSION`
use the public form. `GET /api/version` returns both as `version` and
`python_version`, without filesystem paths or machine details. For a local
default server, open <http://127.0.0.1:8000/api/version>. Include `version`
when reporting a problem. Standalone launcher version reporting will use the
same public identity.

Application version numbers are not save compatibility profiles. This metadata
update leaves the existing save schema and `bowl-bound-m21-v1` engine profile
unchanged. Alpha releases may still have known limitations; keep copies of
saves before upgrading. Never delete/reuse an already published tag.
