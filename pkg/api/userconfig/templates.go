/*
Copyright 2019 Cortex Labs, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

package userconfig

import (
	"fmt"
	"regexp"
	"strings"

	"github.com/cortexlabs/cortex/pkg/api/resource"
	s "github.com/cortexlabs/cortex/pkg/api/strings"
	cr "github.com/cortexlabs/cortex/pkg/utils/configreader"
	"github.com/cortexlabs/cortex/pkg/utils/util"
)

var templateVarRegex = regexp.MustCompile("\\{\\s*([a-zA-Z0-9_-]+)\\s*\\}")

type Templates []*Template

type Template struct {
	Name string `json:"name" yaml:"name"`
	YAML string `json:"yaml" yaml:"yaml"`
}

var templateValidation = &cr.StructValidation{
	StructFieldValidations: []*cr.StructFieldValidation{
		&cr.StructFieldValidation{
			StructField: "Name",
			StringValidation: &cr.StringValidation{
				Required:                   true,
				AlphaNumericDashUnderscore: true,
			},
		},
		&cr.StructFieldValidation{
			StructField: "YAML",
			StringValidation: &cr.StringValidation{
				Required: true,
			},
		},
		typeFieldValidation,
	},
}

func (templates Templates) Validate() error {
	dups := util.FindDuplicateStrs(templates.Names())
	if len(dups) > 0 {
		return ErrorDuplicateConfigName(dups[0], resource.TemplateType)
	}

	return nil
}

func (templates Templates) Names() []string {
	names := make([]string, len(templates))
	for i, template := range templates {
		names[i] = template.Name
	}
	return names
}

func (templates Templates) Map() map[string]*Template {
	m := make(map[string]*Template)
	for _, template := range templates {
		m[template.Name] = template
	}
	return m
}

func (template *Template) VariableNames() []string {
	matches := templateVarRegex.FindAllStringSubmatch(template.YAML, -1)
	variableSet := make(map[string]struct{})
	for _, match := range matches {
		variableSet[match[1]] = struct{}{}
	}

	variables := make([]string, len(variableSet))
	i := 0
	for v := range variableSet {
		variables[i] = v
		i++
	}
	return variables
}

func (template *Template) Populate(emb *Embed) (string, error) {
	templateVariables := make(map[string]string)
	variableNames := template.VariableNames()
	for _, name := range variableNames {
		if _, ok := emb.Args[name]; !ok {
			return "", ErrorTemplateMissingArg(template, name)
		}

		replacementStr := s.ObjFlat(emb.Args[name])
		templateVariables[name] = s.TrimPrefixAndSuffix(replacementStr, `"`)
	}

	// generate weird string that users probably wont use
	leftReplace := "🌜"
	rightReplace := "🌛"
	populatedTemplate := template.YAML

	// normalize e.g. { feature } into {feature}
	populatedTemplate = templateVarRegex.ReplaceAllString(populatedTemplate, "{$1}")

	populatedTemplate = strings.Replace(populatedTemplate, "{{", leftReplace, -1)
	populatedTemplate = strings.Replace(populatedTemplate, "}}", rightReplace, -1)
	for argName := range emb.Args {
		if _, ok := templateVariables[argName]; !ok {
			return "", ErrorTemplateExtraArg(template, argName)
		}

		populatedTemplate = strings.Replace(populatedTemplate, fmt.Sprintf("{%s}", argName), templateVariables[argName], -1)
	}
	populatedTemplate = strings.Replace(populatedTemplate, leftReplace, "{", -1)
	populatedTemplate = strings.Replace(populatedTemplate, rightReplace, "}", -1)

	return populatedTemplate, nil
}

func (template *Template) GetName() string {
	return template.Name
}

func (template *Template) GetResourceType() resource.Type {
	return resource.TemplateType
}
