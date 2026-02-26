rules = env['ir.rule'].search([('model_id.model', '=', 'smart.radar.client.config')])
for rule in rules:
    print(f"Deleting rule: {rule.name}")
rules.unlink()
env.cr.commit()
print("Rules deleted successfully.")
