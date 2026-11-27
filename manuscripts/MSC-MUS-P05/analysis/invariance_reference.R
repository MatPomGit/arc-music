# Synthetic two-group ordinal CFA reference, no latent means exported.
args <- commandArgs(trailingOnly=TRUE)
if (length(args)!=2L) stop("usage: invariance_reference.R input.csv output.csv")
suppressPackageStartupMessages(library(lavaan))
suppressPackageStartupMessages(library(semTools))
x <- read.csv(args[1], check.names=FALSE)
items <- paste0("item",1:8)
if (!identical(names(x),c("group",items)) || anyNA(x) ||
    !identical(sort(unique(x$group)),1:2)) stop("Invalid input schema")
for (g in 1:2) {
    y <- x[x$group==g,items,drop=FALSE]
    if (nrow(y)<150 || any(!vapply(y,function(col) identical(sort(unique(col)),0:4),logical(1))))
        stop("Insufficient complete group or ordinal categories")
}
model <- "f1 =~ item1 + item2 + item3 + item4
          f2 =~ item5 + item6 + item7 + item8"
names_test <- c("configural_1","configural_2","threshold_shape","threshold_loading","threshold_loading_intercept")
constraints <- list(character(0),"thresholds",c("thresholds","loadings"),
                    c("thresholds","loadings","intercepts"))
safe <- function(expr) {
    warnings <- character()
    result <- tryCatch(withCallingHandlers({
        fit <- force(expr)
        if (!lavInspect(fit,"converged")) list(status="NONCONVERGED",fit=NULL,reason="nonconverged")
        else {
            cov <- lavInspect(fit,"cov.lv")
            if (is.matrix(cov)) cov <- list(cov)
            theta <- lavInspect(fit,"theta")
            if (is.matrix(theta)) theta <- list(theta)
            proper <- isTRUE(lavInspect(fit,"post.check")) &&
                all(vapply(cov,function(m) min(eigen(cov2cor(m),symmetric=TRUE,only.values=TRUE)$values)>.01,logical(1))) &&
                all(vapply(theta,function(m) min(diag(m))>0,logical(1)))
            list(status=if (proper) "PROPER" else "IMPROPER",fit=if(proper) fit else NULL,
                 reason=if(proper) "" else "inadmissible covariance or residual variance")
        }
    },warning=function(w) {
        warnings <<- c(warnings,conditionMessage(w))
        invokeRestart("muffleWarning")
    }),error=function(err) list(status="ERROR",fit=NULL,reason=conditionMessage(err)))
    result$warnings <- paste(unique(warnings),collapse="; ")
    result
}
row <- function(name,status,p=NA_real_,df=NA_real_,reason="",warnings="") {
    data.frame(test=name,status=status,p_value=p,df=df,reason=reason,warnings=warnings,
       lavaan=as.character(packageVersion("lavaan")),semTools=as.character(packageVersion("semTools")))
}
single <- lapply(1:2,function(g) safe(cfa(model,data=x[x$group==g,],ordered=items,
                                      estimator="WLSMV",parameterization="theta",std.lv=TRUE)))
output <- lapply(1:2,function(g) {
    a <- single[[g]]
    if(a$status!="PROPER") return(row(names_test[g],a$status,reason=a$reason,warnings=a$warnings))
    p <- fitMeasures(a$fit,"pvalue.scaled")
    df <- fitMeasures(a$fit,"df.scaled")
    if(!is.finite(p)||p<0||p>1||!is.finite(df)||df<=0) return(row(names_test[g],"ERROR",reason="invalid scaled fit statistic"))
    row(names_test[g],"PROPER",unname(p),unname(df),warnings=a$warnings)
})
multi <- lapply(constraints,function(eq) safe({
    syntax <- measEq.syntax(configural.model=model,data=x,ordered=items,
        parameterization="theta",ID.fac="std.lv",ID.cat="Wu.Estabrook.2016",
        group="group",group.equal=eq)
    cfa(as.character(syntax),data=x,ordered=items,group="group",
        estimator="WLSMV",parameterization="theta")
}))
for (j in 2:4) {
    a <- multi[[1]]; b <- multi[[j]]
    if (a$status!="PROPER" || b$status!="PROPER") {
        output[[j+1]] <- row(names_test[j+1],"UNAVAILABLE",
            reason=paste("configural",a$status,a$reason,"restricted",b$status,b$reason),
            warnings=paste(a$warnings,b$warnings,sep="; "))
        next
    }
    # Cumulative restrictions compared to the same configural model, matching
    # the scientific null family; robust difference statistic, not subtraction
    # of two scaled chi-squares.
    output[[j+1]] <- tryCatch({
        tab <- lavTestLRT(a$fit,b$fit,method="satorra.2000",A.method="delta")
        p <- tail(tab[["Pr(>Chisq)"]],1)
        df <- tail(tab[["Df diff"]],1)
        if(length(p)!=1||!is.finite(p)||p<0||p>1||length(df)!=1||!is.finite(df)||df<=0)
            stop("Invalid robust difference statistic")
        row(names_test[j+1],"PROPER",p,df,warnings=paste(a$warnings,b$warnings,sep="; "))
    },error=function(err) row(names_test[j+1],"ERROR",reason=conditionMessage(err)))
}
write.csv(do.call(rbind,output),args[2],row.names=FALSE)
