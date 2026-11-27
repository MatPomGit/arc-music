# Paired independent ordinal reference comparisons on synthetic records only.
args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 2L) stop("usage: model_reference.R input.csv output.csv")
suppressPackageStartupMessages(library(lavaan))
x <- read.csv(args[1], check.names = FALSE)
items <- paste0("item", seq_len(35))
factors <- paste0("factor", seq_len(7))
if (!identical(names(x), items) || anyNA(x) || nrow(x) <= 35L ||
    any(!vapply(x, function(col) identical(sort(unique(col)), 0:4), logical(1)))) {
    stop("Insufficient complete records or incomplete ordinal categories")
}
first_order <- paste(vapply(seq_len(7), function(j) {
    paste(factors[j], "=~", paste(items[(j-1L)*5L+seq_len(5)], collapse=" + "))
}, character(1)), collapse="\n")
models <- list(one_factor=paste("general =~", paste(items, collapse=" + ")),
               correlated_seven=first_order,
               higher_order=paste(first_order, paste("general =~", paste(factors, collapse=" + ")), sep="\n"))
assess <- function(name) {
    warnings <- character()
    row <- data.frame(model=name, status="ERROR", n=nrow(x),
                      minimum_uniqueness=NA_real_, minimum_factor_eigenvalue=NA_real_,
                      cfi_scaled=NA_real_, tli_scaled=NA_real_, rmsea_scaled=NA_real_,
                      srmr=NA_real_, p_scaled=NA_real_, reason="", warnings="",
                      lavaan=as.character(packageVersion("lavaan")), stringsAsFactors=FALSE)
    tryCatch(withCallingHandlers({
        fit <- cfa(models[[name]], data=x, ordered=items, estimator="WLSMV",
                   std.lv=TRUE, parameterization="delta", missing="listwise")
        if (!lavInspect(fit, "converged")) {
            row$status <- "NONCONVERGED"
        } else {
            latent <- lavInspect(fit, "cov.lv")
            row$minimum_factor_eigenvalue <- min(eigen(cov2cor(latent), symmetric=TRUE, only.values=TRUE)$values)
            row$minimum_uniqueness <- min(diag(lavInspect(fit, "theta")))
            proper <- lavInspect(fit,"post.check") &&
                row$minimum_uniqueness > .01 && row$minimum_factor_eigenvalue > .01
            row$status <- if (proper) "PROPER" else "IMPROPER"
            fm <- fitMeasures(fit, c("cfi.scaled","tli.scaled","rmsea.scaled","srmr","pvalue.scaled"))
            row[,c("cfi_scaled","tli_scaled","rmsea_scaled","srmr","p_scaled")] <- as.list(unname(fm))
        }
    }, warning=function(w) {
        warnings <<- c(warnings, conditionMessage(w))
        invokeRestart("muffleWarning")
    }), error=function(e) {
        row$status <<- "ERROR"
        row$reason <<- conditionMessage(e)
    })
    row$warnings <- paste(unique(warnings), collapse="; ")
    row
}
write.csv(do.call(rbind, lapply(names(models), assess)), args[2], row.names=FALSE)
