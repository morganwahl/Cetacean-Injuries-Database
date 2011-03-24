from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django import forms
from django.utils.safestring import mark_safe

from templatetags.merge_display import display_merge_row

class FieldlessModel(models.Model):
    class Meta:
        abstract= True

class MergeForm(forms.ModelForm):
    '''
    Given a source and destination instance of a Model and a corresponding
    ModelForm, returns a subclass of the ModelForm whose fields' HTML has the
    data for both instances. When this form is saved, it saves it's contents
    to the destination instance, changes all references to the sources 
    instance to the destination, and *deletes* the source instance.

    ForeignKeys _to_ the source instance are simply switched to the destination. 
    ManyToMany refs are merged (i.e. the set of refs to source is unioned with 
    the set of refs to dest). OneToOne references ought to be merged 
    recursively...
    '''

    # TODO could this be a mix-in superclass for ModelForms?
    
    # TODO rename, since it's both o2o and fk
    @classmethod
    def _get_fk_refs(cls, instance):
        '''
        Get all the ForeignKey and OneToOne references _to_ an instance. 
        Returns a dict like {<other model>: {<other instance primary key>: [<other fields>]}}
        '''
        
        results = {}
        def _results_add(other_model, other_instance, other_field):
            # It's important to store only the primary key since we 
            # don't want to have multiple in-memory instance of the same
            # object in the database
            pk = other_instance.pk
            if not other_model in results:
                results[other_model] = {}
            if not pk in results[other_model]:
                results[other_model][pk] = []
            results[other_model][pk].append(other_field)        
        
        rel_objs = instance._meta.get_all_related_objects()
        for rel_obj in rel_objs:
            # note that OneToOneFields are also ForeignKeys
            if isinstance(rel_obj.field, models.OneToOneField):
                # this may be the 'parent_link' field used to implement multi-
                # table inheritance.
                if rel_obj.field.rel.parent_link:
                    # if so, there must not be anything on the other side of
                    # the relation, since that would mean this instance isn't
                    # the most specific one
                    try:
                        getattr(instance, rel_obj.get_accessor_name())
                        # TODO not the best error message
                        raise ValueError("Can't merge instances of non-abstract superclasses unless there is no data for any subclass.")
                    except ObjectDoesNotExist:
                        pass
                else:
                    try:
                        other_instance = getattr(instance, rel_obj.get_accessor_name())
                        _results_add(rel_obj.model, other_instance, rel_obj.field)
                    except ObjectDoesNotExist:
                        pass
            else:
                other_queryset = getattr(instance, rel_obj.get_accessor_name())
                for other_instance in other_queryset.all():
                    _results_add(rel_obj.model, other_instance, rel_obj.field)
        
        return results

    @classmethod
    def _get_m2m_refs(cls, instance):
        '''
        Get all the ManyToManyField references _to_ an instance. Returns a 
        tuple of triples of the form: (<other Model>, <other field>, 
        <other instance primary key>).
        '''
        
        related_objects = instance._meta.get_all_related_many_to_many_objects()
        results = []
        for ro in related_objects:
            other_queryset = getattr(instance, ro.get_accessor_name()).all()
            for other_instance in other_queryset:
                results.append((
                    ro.model,
                    ro.field,
                    other_instance.pk,
                ))
        
        return tuple(results)
    
    @classmethod
    def _get_o2o_refs_from(cls, instance):
        '''
        Get all the OneToOne references _from_ an instance. Returns a 
        dictionary of fields keyed to their names.
        '''
        
        results = {}
        inheritance_fields = instance._meta.parents.values()
        for field in instance._meta.fields:
            if isinstance(field, models.OneToOneField):
                if not field.auto_created:
                    ro = field.related
                    other_instance = getattr(instance, field.name)
                    results[field.name] = field
        
        return results
    
    def __init__(self, source, destination, data=None, **kwargs):
        if not isinstance(source, models.Model):
            raise TypeError("source isn't a Model instance!")
        if not isinstance(destination, models.Model):
            raise TypeError("destination isn't a Model instance!")
            # source can be a superclass of destination, but not the other way
            # around.
        if not isinstance(destination, source.__class__):
            raise TypeError("destination type %s can't have source type %s merged into it!"% (destination.__class__, source.__class__))
        # allow passing in of unsaved instances
        if destination.pk and source.pk:
            if source.pk == destination.pk:
                raise ValueError("can't merge something with itself!")
        
        super(MergeForm, self).__init__(data, instance=destination, **kwargs)
        self.source = source
        self.destination = destination
        
        # TODO start the transaction here! We're getting queryset of other
        # instances to display, then later saving changes to those instances.
        
        # allow passing in of unsaved instances
        if self.source.pk:
            self.source_fk_refs = self._get_fk_refs(self.source)
            self.source_m2m_refs = self._get_m2m_refs(self.source)
        
        if self.destination.pk:
            self.destination_fk_refs = self._get_fk_refs(self.destination)
            self.destination_m2m_refs = self._get_m2m_refs(self.destination)

        # OneToOneFields in the model we're merging need special handling. Since
        # they can only point to one other instance, we need merge forms for
        # the instance pointed to by the field in destination and source. We
        # also need to add a boolean field to the form to mark the 
        # OneToOneField as simply null in the destination.
        source_o2o_from_refs = self._get_o2o_refs_from(self.source)
        destination_o2o_from_refs = self._get_o2o_refs_from(self.destination)
        self.subforms = {}
        self.has_field_names = {}
        # avoid circular imports
        # TODO better place for this
        from cetacean_incidents.apps.locations.models import Location
        from cetacean_incidents.apps.locations.forms import LocationMergeForm
        from cetacean_incidents.apps.vessels.forms import VesselInfoMergeForm
        from cetacean_incidents.apps.vessels.models import VesselInfo
        subform_classes = {
            Location: LocationMergeForm,
            VesselInfo: VesselInfoMergeForm,
        }
        
        # note that source_o2o_from_refs.key() will always be a subset of 
        # destination_o2o_from_refs.keys(), since we insured destination is an
        # instance of source.__class__
        for fieldname, field in destination_o2o_from_refs.items():
            destination_instance = getattr(destination, fieldname)
            if fieldname in source_o2o_from_refs.keys():
                source_instance = getattr(source, fieldname)
            else:
                source_instance = None
            subform_prefix = fieldname
            if self.prefix:
                subform_prefix = self.prefix + '-' + subform_prefix
            
            bool_field_name = 'has_' + fieldname
            while bool_field_name in self.fields.keys():
                bool_field_name = bool_field_name + '_o2o'
            self.fields[bool_field_name] = forms.BooleanField(
                required= False,
                initial= destination_instance is not None,
                label= 'has ' + field.verbose_name + ' info',
            )
            self.has_field_names[fieldname] = bool_field_name
            del self.fields[fieldname]

            # TODO is parent_model the the best way to get the Model at the 
            # other end of a OneToOneField?
            other_model = field.related.parent_model

            # the 'has_*' field will take care of null-values for the o2o field.
            # If these are None, go ahead and instantiate them.
            if destination_instance is None:
                destination_instance = other_model()
            if source_instance is None:
                source_instance = other_model()
            
            if not other_model in subform_classes.keys():
                raise NotImplementedError("%s needs a MergeForm subclass" % field.related.parent_model)
            
            # TODO this is a recursive call! need some check to avoid infinite
            # recursion
            self.subforms[fieldname] = subform_classes[other_model](
                destination= destination_instance,
                source= source_instance,
                data= data,
                prefix= subform_prefix,
            )
            
    # display_o2o_merge_row.html uses checkboxhider.js
    class Media:
        js = (settings.JQUERY_FILE, 'checkboxhider.js')
            
    @staticmethod
    def _get_fk_refs_display(fk_refs):
        result = {}
        for model, model_dict in fk_refs.items():
            new_model_dict = {}
            for pk, fields in model_dict.items():
                new_model_dict[model.objects.get(pk=pk)] = map(lambda f: f.verbose_name, fields)
            if len(new_model_dict) == 1:
                model_name = model._meta.verbose_name
            else:
                model_name = model._meta.verbose_name_plural
            result[model_name] = new_model_dict
        return result
    
    @property
    def source_fk_refs_display(self):
        return self._get_fk_refs_display(self.source_fk_refs)
    
    @property
    def destination_fk_refs_display(self):
        return self._get_fk_refs_display(self.destination_fk_refs)

    @staticmethod
    def _get_m2m_refs_display(m2m_refs):
        return map(
            lambda t: (t[0]._meta.verbose_name, t[1].verbose_name, t[0].objects.get(pk=t[2])),
            m2m_refs
        )

    @property
    def source_m2m_refs_display(self):
        return self._get_m2m_refs_display(self.source_m2m_refs)
    
    @property
    def destination_m2m_refs_display(self):
        return self._get_m2m_refs_display(self.destination_m2m_refs)

    def save(self, commit=True):
        # FIXME uncommited saving is uncertain
        if not commit:
            raise NotImplementedError("uncommited saving of MergeForms is not yet implemented")
        
        if self.source.pk:
            for (other_model, other_field, other_instance_pk) in self.source_m2m_refs:
                other_instance = other_model.objects.get(pk=other_instance_pk)
                accessor = getattr(other_instance, other_field.name)
                # don't remove source; the references to it will disappear when it
                # is deleted.
                #accessor.remove(self.source)
                accessor.add(self.destination)
        
        if self.source.pk:
            for other_model, model_dict in self.source_fk_refs.items():
                for other_instance_pk, fields in model_dict.items():
                    other_instance = other_model.objects.get(pk=other_instance_pk)
                    for f in fields:
                        if isinstance(f, models.OneToOneField):
                            # set o2o refs to the source to None
                            setattr(other_instance, f.name, None)
                        else:
                            # switch fk refs from the source to the destination
                            setattr(other_instance, f.name, self.destination)
                    other_instance.save()
        
        # handle o2o refs from this model
        for fieldname in self.subforms.keys():
            has_field_name = self.has_field_names[fieldname]
            if self.cleaned_data[has_field_name]:
                saved_instance = self.subforms[fieldname].save()
                setattr(self.destination, fieldname, saved_instance)
            else:
                setattr(self.destination, fieldname, None)
        
        result = super(MergeForm, self).save(commit=commit)
        
        if self.source.pk:
            # before deleting self.source, re-instantiate it
            self.source.__class__.objects.get(pk=self.source.pk).delete()
        
        return result
    
    # FIXME this method is never called
    def pre_save(self):
        for inst in self._save_m2m_todo:
            inst.save()
        
        self.source.delete()

