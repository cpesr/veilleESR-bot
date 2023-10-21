load("results.RData")

labvarfun <- function(x,pad,wrap=50) {
  x <- str_pad(x, pad, side = "left")
  x <- str_wrap(x,wrap)
  x <- str_replace(x," ; ","\n")
#  x <- str_replace(x,"ATEN, ","ATEN,\n")
  x[is.na(x)] <- "Non renseigné"
  return(x)
}

plot_caracteristique <- function(variable, title="", palette="Set2", pad=0, wrap=65, width=0.9) {
  results %>%
    rename(var = !!sym(variable)) %>%
    summarise(nb = n(), .by = var) %>%
    mutate(part = nb / sum(nb)) %>%
    #mutate(var = fct_explicit_na(var,"Sans réponse")) %>%
    filter(!is.na(var)) %>%
    ggplot(aes(y=var,x=nb,fill=var)) + 
    geom_col(color="black",size=0.1,width = width) +
    scale_y_discrete(name=variable, limits=rev, labels= ~ labvarfun(.x,pad,wrap) ) +
    #scale_x_continuous(labels=scales::percent, name = "Part des réponses") +
    scale_x_continuous(name = "Nombre de répondants") +
    scale_fill_brewer(palette=palette, na.value="grey", direction = -1) +
    ggtitle(title) +
    theme(legend.position = "none", 
          axis.title.y = element_blank(),
          plot.title.position = "plot", plot.title = element_text(hjust = 1))
}

plot_caracteristique('sexe')
# plot_caracteristique('categorie',"Catégorie")

plot_etab <- function() {
  results %>%
    mutate(typeetab.other. = ifelse(is.na(typeetab.other.),"Non","Oui")) %>%
    pivot_longer(starts_with("typeetab"), names_to = "Type", values_to = "Affectation") %>%
    summarise(Nombre = n(), .by = c(Type,Affectation)) %>%
    mutate(part = Nombre/sum(Nombre), .by = Type) %>%
    mutate(Type = factor(Type,levels=etab.factor$levels,labels=etab.factor$labels)) %>%
    arrange(Type,Affectation) %>%
    filter(Affectation == "Oui") %>%
    ggplot(aes(y=Type,x=Nombre,fill=Type)) + 
      geom_col(color="black",size=0.1) +
      scale_y_discrete(name="Type d'établissement", limits=rev) +
      # scale_x_continuous(labels=scales::percent, name = "Part des réponses") +
      scale_x_continuous(name = "Nombre de répondants") +
      ggtitle("Quel est votre établissement ?") +
      theme(legend.position = "none", 
            axis.title.y = element_blank(),
            plot.title.position = "plot", plot.title = element_text(hjust = 1))
}

# plot_etab()


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
    geom_col(alpha=0.8,color="black", size=0.1) +
    geom_vline(xintercept = 0, size=0.1, color="white") +
    scale_x_continuous(limits=c(-1,1), name = "Part des répondants", 
                       labels = ~ scales::percent(abs(.x))) +
    scale_y_discrete(limits=rev, labels = ~ str_wrap(.x,45)) +
    scale_fill_brewer(palette='RdYlBu', limits = l) 
}


# plot_bloc("conditions",conditions.factor)
#plot_bloc("evolution",conditions.factor)
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
    complete(Question,Réponse,fill = list(part=0)) %>%
    filter(startsWith(as.character(Réponse), "Ne connait pas")) %>%
    
    ggplot(aes(x=part, y=Question, fill=Réponse)) +
    geom_col(alpha=0.8, color="black", size=0.1) +
    scale_x_continuous(name = "Part des répondants", 
                       labels = ~ scales::percent(abs(.x))) +
    scale_y_discrete(limits=rev, labels = ~ str_wrap(.x,45)) +
    scale_fill_brewer(palette='Dark2') 
}

# plot_bloc_connait("confiance",confiance.factor)
# plot_bloc_connait("reformes",reformes.factor)


# plot_bloc_legend <- function(bloc) {
#   p <- results %>%
#     select(id,starts_with(bloc)) %>%
#     pivot_longer(-id, values_to = "Réponse", names_to = "Question") %>%
#     filter(!is.na(Réponse)) %>%
#     ggplot(aes(x=Question,y=Réponse,fill=Réponse)) +
#     geom_col() +
#     theme(legend.position = "right", legend.title = element_blank()) 
#   return(cowplot::get_legend(p))
# }


# plot_bloc_grid <- function(bloc,bloc.factor) {
#   p1 <- plot_bloc(bloc,bloc.factor) + 
#     theme(legend.title=element_blank(),legend.position = "right")
#   p2 <- plot_bloc_connait(bloc,bloc.factor) + 
#     theme(legend.title=element_blank(),legend.position = "right")
#   
#   cowplot::plot_grid(nrow=2,rel_heights = c(6,1),
#     cowplot::plot_grid(nrow=1,rel_widths = c(6,2), align = "h",
#       p1 + theme(legend.position = "none"),
#       p2 + theme(axis.text.y = element_blank(), legend.position = "none")
#     ),
#     cowplot::plot_grid(nrow=1,rel_widths = c(3,1), cowplot::get_legend(p1),cowplot::get_legend(p2))
#   )
# }

plot_bloc_grid <- function(bloc,bloc.factor) {
  p1 <- plot_bloc(bloc,bloc.factor) + theme(legend.title = element_blank())
  p2 <- plot_bloc_connait(bloc,bloc.factor) + 
    theme(axis.text.y = element_blank(), axis.title.y = element_blank(), legend.title = element_blank())
  
  cowplot::plot_grid(nrow=1, rel_widths = c(6,2), align = "h", p1, p2)
}


# plot_bloc_grid("confiance",confiance.factor)
# plot_bloc_grid("reformes",reformes.factor)


# results %>%
#   
#   
#   select(id,starts_with(bloc)) %>%
#   pivot_longer(-id, values_to = "Réponse", names_to = "Question") %>%
#   filter(!is.na(Réponse)) %>%
#   ggplot()



plot_bloc_percent <- function(bloc, pad=35, plot=TRUE) {
  df <- results %>%
    select(id,starts_with(bloc)) %>%
    pivot_longer(-id, values_to = "Réponse", names_to = "Question") %>%
    filter(!is.na(Réponse)) %>%
    filter( !startsWith(as.character(Réponse), "Ne connait pas")) %>%
    mutate(Réponse = droplevels(Réponse)) %>%
    summarise(nb.questions = n(), .by=Réponse) %>%
    mutate(part = nb.questions / sum(nb.questions)) %>%
    arrange(Réponse)
  
  if(!plot) return(
    df %>% 
      mutate(cs = scales::percent(cumsum(part))) %>%
      arrange(desc(Réponse)) %>%
      mutate(csr = scales::percent(cumsum(part)))
  )
                     
  part <- df %>%
    filter(as.numeric(Réponse) > length(levels(Réponse))/2+1) %>%
    summarise(part = scales::percent(sum(part))) %>%
    pull(part)

  p <- df %>%
    ggplot(aes(x=1,y=part,fill=Réponse,color=Réponse)) +
    geom_col(color="black",size=0.1) +
    annotate("text",x=-2,y=0,label=part,size=18,fontface="bold") +
    coord_polar(theta="y") +
    xlim(c(-2, 1.5)) +
    scale_color_brewer(palette='RdYlBu', labels = ~ str_pad(.x, pad, side = "right")) +
    scale_fill_brewer(palette='RdYlBu', labels = ~ str_pad(.x, pad, side = "right")) +
    theme_void() +
    theme(legend.position = "left")
  return(p)
}
# plot_bloc_percent("conditions")
# plot_bloc_percent("evolution")
# plot_bloc_percent("optimisme")
# plot_bloc_percent("confiance")
# plot_bloc_percent("reformes")

# plot_bloc_percent("conditions", FALSE)


nb_repondants <- function(variable,valeur=NA) {
  df <- results %>%
    summarise(nb=n(),.by=(!!sym(variable)))
  
  if(!is.na(valeur)) 
    return(df %>% filter(!!sym(variable) == valeur) %>% pull(nb))
  
  return(df)
}

# nb_repondants("sexe")
# nb_repondants("sexe","Autre")

plot_pop <- function(variable) {
  df <- results %>%
    rename(var = !!sym(variable)) %>%
    select(id,var,conditions.generale.:reformes.LPPR.) %>%
    pivot_longer(-c(id,var), values_to = "Réponse", names_to = "Question") %>%
    filter(!is.na(Réponse),!is.na(var)) %>%
    filter( !startsWith(as.character(Réponse), "Ne connait pas")) %>%
    mutate(Réponse = droplevels(Réponse)) %>%
    mutate(bloc = gsub("\\..*","",Question)) %>%
    summarise(nb = n(), .by=c(bloc,var,Réponse)) %>%
    arrange(bloc,var,Réponse) %>%
    mutate(part = nb / sum(nb), .by = c(bloc,var)) %>%
    mutate(Réponse2 = (as.numeric(Réponse)-1)%%7) 
  
  df <- bind_rows(
    df %>% filter(Réponse2 < 3) %>% mutate(y = -part),
    df %>% filter(Réponse2 > 3) %>% mutate(y = part),
    df %>% filter(Réponse2 == 3) %>% mutate(y = part / 2),
    df %>% filter(Réponse2 == 3) %>% mutate(y = - part / 2)) %>%
    arrange(var,Réponse)
  

  df %>%
    mutate(Réponse2 = as.character(Réponse2)) %>%
    ggplot(aes(x=y, y=var, fill=Réponse2)) +
    geom_col(alpha=0.8,color="black", size=0.1) +
    geom_vline(xintercept = 0, size=0.1, color="white") +
    scale_x_continuous(limits=c(-1,1), name = "Part des répondants", 
                       labels = ~ scales::percent(abs(.x))) +
    scale_y_discrete(limits=rev, labels = ~ str_wrap(.x,45)) +
    scale_fill_brewer(palette='RdYlBu') +
    facet_wrap(.~bloc)
}


# plot_pop("sexe")


plot_pop2 <- function(variable,blocs,bloc.factor,palette="Set2",size=4) {
  df <- results %>%
    rename(var = !!sym(variable)) %>%
    select(id,var,starts_with(blocs)) %>%
    pivot_longer(-c(id,var), values_to = "Réponse", names_to = "Question") %>%
    filter(!is.na(Réponse),!is.na(var)) %>%
    filter( !startsWith(as.character(Réponse), "Ne connait pas")) %>%
    mutate(Réponse = droplevels(Réponse)) %>%
    mutate(bloc = str_to_title(gsub("\\..*","",Question))) %>%
    mutate(Question = factor(
      gsub("([a-z]*)\\.(.*)","\\2",Question),
      levels = bloc.factor$levels,
      labels = bloc.factor$lab,
    )) %>%
    mutate(Réponse2 = (as.numeric(Réponse)-1)%%7) %>%
    summarise(Score = mean(Réponse2), .by=c(var,bloc,Question)) %>%
    mutate(Score.diff = Score - mean(Score), .by=c(bloc,Question)) %>%
    arrange(var,bloc,Question) 
  
  # return(df)
  

  df %>%
    ggplot(aes(x=Score.diff, y=Question, shape=var, fill=var)) +
    geom_vline(xintercept = 0, fill="grey") +
    geom_point(size=size, stroke=0.2) +
    facet_wrap(bloc~.) +
    scale_y_discrete(limits=rev,name="") +
    scale_fill_brewer(palette=palette, name="", direction=-1) +
    scale_x_continuous(name="Ecart au score moyen") +
    scale_shape_manual(name="", values=c(21,24,22,23)) +
    theme(legend.position = "right", strip.text.x = element_text(size = 14))
}


plot_pops <- function(variable, palette="Set2", angle = 0) {
  
    cowplot::plot_grid(ncol=1,
      plot_pop2(variable,c("conditions","optimisme","evolution"), conditions.factor,palette) ,
      cowplot::plot_grid(ncol=3, rel_widths = c(1,1.5,1),
        plot_pop2(variable,"reformes", reformes.factor,palette) + theme(legend.position = "None"),
        plot_pop2(variable,"confiance", confiance.factor,palette,2)+ theme(legend.position = "None"),
        plot_caracteristique(variable, palette = palette, width=0.5) + 
          scale_y_discrete(limits=identity) +
          coord_flip() + 
          ggtitle("Nombre de répondants") +
          theme(axis.title.x = element_blank(), axis.text.x = element_text(angle = angle)) 
        )
    )
}

# plot_pops("sexe")
# plot_pops("anciennete","PRGn")
# plot_pops("metier.grp","Set1")
# plot_pops("statut.grp","Accent")
# plot_pops("categorie.grp","Dark2")
# plot_pops("responsabilites.grp","Oranges")


