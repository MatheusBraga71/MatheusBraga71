# Cards do perfil com GitHub Actions

O workflow `.github/workflows/profile-stats.yml` consulta diretamente a API GraphQL
do GitHub e executa `scripts/generate_profile.py`, que usa apenas a biblioteca padrão
do Python. Os quatro SVGs ficam versionados em `assets/` e são exibidos pelo README.
Não é necessário hospedar um servidor, ativar GitHub Pages ou criar um token pessoal.

## Ativar

1. Faça commit e push dos arquivos novos e do README para a branch `main`.
2. Em **Actions → Update profile stats**, acompanhe a primeira execução automática.
   Você também pode iniciar uma execução em **Run workflow** na branch principal.
3. Aguarde o commit `chore: update profile stats` do bot. Ele substitui as imagens
   iniciais, que indicam que a primeira atualização está pendente, pelos dados reais.

O workflow solicita `contents: write` para publicar os SVGs usando o `GITHUB_TOKEN`
automático. Se houver erro de permissão no push, confira as políticas em
**Settings → Actions → General → Workflow permissions** e as regras da branch.
Uma branch que exige pull request pode impedir o commit direto do bot.

## Atualização e métricas

- Execução diária às **06:23 de Brasília (09:23 UTC)**, além da execução manual e
  de pushes que alterem o gerador ou o workflow. O horário agendado pode atrasar.
- Stats: contribuições, commits, PRs, issues e reviews nos últimos **365 dias**,
  de acordo com as regras de contagem do calendário do GitHub; não são commits
  acumulados desde a criação da conta.
- Linguagens: percentual de bytes de código nos repositórios públicos do usuário,
  excluindo forks. Mostra até oito linguagens, com percentuais relativos ao total
  de todas as linguagens. Não representa tempo de uso ou nível de domínio.
- Streak: sequência atual, maior sequência **dentro dos 365 dias consultados** e
  número de dias ativos. Hoje sem contribuições ainda não interrompe a sequência
  de ontem. As datas usadas no cálculo são UTC.
- Atividade: contribuições diárias nos últimos **30 dias**.

O token automático não dá acesso geral aos repositórios privados da conta.
O calendário pode incluir contagens privadas anônimas se forem disponibilizadas
pelo GitHub conforme as configurações do perfil; esta solução não promete contabilizar
toda atividade privada. Não replica o antigo parâmetro `count_private=true`.

Se a API falhar, o job falha antes do commit e os SVGs publicados permanecem intactos.
O perfil continua exibindo a última atualização. Antes da primeira execução bem-sucedida,
as imagens exibem uma mensagem de configuração pendente, sem números fictícios.
Outros elementos do README (badges, contador de visitas e ícones) ainda usam seus
respectivos serviços externos.

O GitHub pode desativar agendamentos em repositórios públicos após 60 dias sem
atividade. Se as datas dos cards pararem de mudar, confira a página do workflow.

## Verificação local

```powershell
python -m unittest discover -s scripts -p 'test_*.py'
```

Os testes usam dados simulados, sem rede. Para gerar dados reais localmente, o script
requer `GH_TOKEN` com acesso à API e `PROFILE_USERNAME` no ambiente. No Actions,
essas variáveis já são configuradas pelo YAML.

## Referências

- [Autenticação automática com GITHUB_TOKEN](https://docs.github.com/en/actions/tutorials/authenticate-with-github_token)
- [Eventos e agendamento de workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)
- [API GraphQL de usuários e contribuições](https://docs.github.com/en/graphql/reference/users)
