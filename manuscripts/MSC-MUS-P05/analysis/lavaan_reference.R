# Independent ordinal CFA reference for synthetic development.
args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 4L) stop("usage: Rscript lavaan_reference.R data.csv factors items output.csv")
suppressPackageStartupMessages(library(lavaan))
x <- read.csv(args[1], check.names = FALSE)
k <- as.integer(args[2])
per_factor <- as.integer(args[3])
items <- paste0("item", seq_len(k * per_factor))
factors <- paste0("factor", seq_len(k))
if (!identical(names(x), items) || anyNA(x) ||
    any(!vapply(x, function(column) identical(sort(unique(column)), 0:4), logical(1)))) {
    stop("Each synthetic item must include all five ordered categories")
}
model <- paste(vapply(seq_len(k), function(j) {
    block <- items[(j-1L) * per_factor + seq_len(per_factor)]
    paste(factors[j], "=~", paste(block, collapse = " + "))
}, character(1)), collapse = "\n")

fit <- cfa(model, data = x, ordered = items, estimator = "WLSMV",
           std.lv = TRUE, parameterization = "delta", missing = "listwise")
converged <- lavInspect(fit, "converged")
proper <- converged && suppressWarnings(lavInspect(fit, "post.check"))
params <- parameterEstimates(fit)
get_rows <- function(op) {
    p <- params[params$op == op, ]
    data.frame(kind = op, lhs = p$lhs, rhs = p$rhs, value = p$est, se = p$se)
}
loading <- get_rows("=~")
correlation <- get_rows("~~")
correlation <- subset(correlation, lhs %in% factors & rhs %in% factors & lhs != rhs)
# Use the same numerical proximity flags, but preserve the lavaan post-check.
lambda <- setNames(loading$value, loading$rhs)[items]
latent <- lavInspect(fit, "cov.lv")
min_eigen <- min(eigen(latent, symmetric = TRUE, only.values = TRUE)$values)
signs <- sign(lambda[seq.int(1L, length(items), by = per_factor)])
names(signs) <- factors
loading$value <- loading$value * signs[loading$lhs]
correlation$value <- correlation$value * signs[correlation$lhs] * signs[correlation$rhs]
fit_probability <- if (converged) fitMeasures(fit, "pvalue.scaled") else NA_real_
metadata <- data.frame(
    kind = "meta", lhs = c("converged", "post_check", "minimum_uniqueness",
                           "minimum_factor_eigenvalue", "wlsmv_p"),
    rhs = as.character(packageVersion("lavaan")),
    value = c(converged, proper, min(1-lambda^2), min_eigen, fit_probability), se = NA_real_
)
write.csv(rbind(metadata, loading, correlation, get_rows("|")), args[4], row.names = FALSE)
