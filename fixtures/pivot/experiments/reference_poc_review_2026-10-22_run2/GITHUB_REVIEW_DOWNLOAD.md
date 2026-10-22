# Download this review package from GitHub

The Ralph Bridge source publisher accepts UTF-8 text files, so the ZIP is stored as numbered Base64 text parts. Download all `review-package.zip.b64.part-*` files from this directory, then concatenate and decode them:

```sh
cat review-package.zip.b64.part-* | base64 --decode > review-package.zip
sha256sum -c package.sha256
```

The editable KiCad project, fabrication outputs, reports and top/bottom renders are also available as individual files in this directory. The ZIP SHA-256 is recorded in `package.sha256`.
