"""Convenção de situação confirmada pelo usuário para a entrada de Transportadoras."""
def is_active(row):
 return str(row.get('complemento') or '').strip().casefold()!='inativo'
