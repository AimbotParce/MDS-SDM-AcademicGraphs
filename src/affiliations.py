
                for affiliation in author["affiliations"]:
                    if not affiliation in unique_organization_names:
                        organizations.writerow({"name": affiliation})
                        unique_organization_names.add(affiliation)
                    isaffiliatedwith.writerow({"authorID": author["authorId"], "organization": affiliation})