# The module was renamed from "launchpad" to "firewatch". This keeps the existing state entries,
# so Terraform renames resources in place where it can instead of creating a second copy.
moved {
  from = module.launchpad
  to   = module.firewatch
}
