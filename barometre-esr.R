load("results.RData")

plot_caracteristique <- function(variable) {
  results %>%
    rename(var = !!sym(variable)) %>%
    summarise(nb = n(), .by = var) %>%
    mutate(part = nb / sum(nb)) %>%
    ggplot(aes(y=var,x=part,fill=var)) + 
    geom_col() +
    scale_y_discrete(name=variable, limits=rev) +
    scale_x_continuous(labels=scales::percent, name = "Part des réponses") +
    theme(legend.position = "none")
}

#plot_caracteristique('sexe')

plot_bloc <- function(bloc,bloc.factor) {
  df <- results %>%
    select(id,starts_with(bloc)) %>%
    pivot_longer(-id, values_to = "Réponse", names_to = "Question") %>%
    filter(!is.na(Réponse)) %>%
    filter( !startsWith(as.character(Réponse), "Ne connait pas")) %>%
    mutate(Réponse = droplevels(Réponse)) %>%
    summarise(nb = n(), .by=c(Question,Réponse)) %>%
    mutate(
      Question = factor(Question,
                        levels = paste0(bloc,".",bloc.factor$levels),
                        labels = bloc.factor$labels) )  %>%
    arrange(Question,Réponse) %>%
    mutate(part = nb / sum(nb), .by = Question)
  

  nl <- length(levels(df$Réponse))/2
  df <- bind_rows(
    df %>% filter(as.numeric(Réponse) < nl) %>% mutate(y = -part),
    df %>% filter(as.numeric(Réponse) > ceiling(nl)) %>% mutate(y = part),
    df %>% filter(as.numeric(Réponse) == ceiling(nl)) %>% mutate(y = part / 2),
    df %>% filter(as.numeric(Réponse) == ceiling(nl)) %>% mutate(y = - part / 2)) %>%
    arrange(Question,Réponse)
  
    
  l <- levels(df$Réponse)
  df %>%
    mutate(Réponse = factor(Réponse, levels = l[c(1:3,7:4)])) %>% 
    ggplot(aes(x=y, y=Question, fill=Réponse)) +
    geom_col(alpha=0.8) +
    geom_vline(xintercept = 0, size=0.1) +
    scale_x_continuous(limits=c(-1,1), name = "Part des répondants", 
                       labels = ~ scales::percent(abs(.x))) +
    scale_y_discrete(limits=rev, labels = ~ str_wrap(.x,45)) +
    scale_fill_brewer(palette='RdYlBu', limits = l) 
}


# plot_bloc("conditions",conditions.factor)
# plot_bloc("evolution",conditions.factor)
# plot_bloc("optimisme",conditions.factor)
# plot_bloc("confiance",confiance.factor)
# plot_bloc("reformes",reformes.factor)


plot_bloc_connait <- function(bloc,bloc.factor) {
  results %>%
    select(id,starts_with(bloc)) %>%
    pivot_longer(-id, values_to = "Réponse", names_to = "Question") %>%
    filter(!is.na(Réponse)) %>%
    mutate(Réponse = droplevels(Réponse)) %>%
    summarise(nb = n(), .by=c(Question,Réponse)) %>%
    mutate(
      Question = factor(Question,
                        levels = paste0(bloc,".",bloc.factor$levels),
                        labels = bloc.factor$labels) )  %>%
    arrange(Question,Réponse) %>%
    mutate(part = nb / sum(nb), .by = Question) %>%
    filter(startsWith(as.character(Réponse), "Ne connait pas")) %>%
  
    ggplot(aes(x=part, y=Question, fill=Réponse)) +
    geom_col(alpha=0.8) +
    scale_x_continuous(name = "Part des répondants", 
                       labels = ~ scales::percent(abs(.x))) +
    scale_y_discrete(limits=rev, labels = ~ str_wrap(.x,45)) +
    scale_fill_brewer(palette='Dark2') 
}

# plot_bloc_connait("confiance",confiance.factor)
# plot_bloc_connait("reformes",reformes.factor)


plot_bloc_legend <- function(bloc) {
  p <- results %>%
    select(id,starts_with(bloc)) %>%
    pivot_longer(-id, values_to = "Réponse", names_to = "Question") %>%
    filter(!is.na(Réponse)) %>%
    ggplot(aes(x=Question,y=Réponse,fill=Réponse)) +
    geom_col() +
    theme(legend.position = "right", legend.title = element_blank()) 
  return(cowplot::get_legend(p))
}


plot_bloc_grid <- function(bloc,bloc.factor) {
  p1 <- plot_bloc("confiance",confiance.factor) + 
    theme(legend.title=element_blank(),legend.position = "right")
  p2 <- plot_bloc_connait("confiance",confiance.factor) + 
    theme(legend.title=element_blank(),legend.position = "right")
  
  cowplot::plot_grid(nrow=1,rel_widths = c(6,2,1), align = "h",
    p1 + theme(legend.position = "none"),
    p2 + theme(axis.text.y = element_blank(), legend.position = "none"),
    cowplot::plot_grid(ncol=1,rel_widths = c(3,1), cowplot::get_legend(p1),cowplot::get_legend(p2))
  )
}

# plot_bloc_grid("confiance",confiance.factor)
# plot_bloc_grid("reformes",reformes.factor)
