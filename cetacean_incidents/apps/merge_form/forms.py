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
    
    @staticmethod    
    def _get_fk_refs_to(instance):
        '''\
        Get every instance with a ForeignKey field (that isn't a OneToOneField) that refers to the given instance. Return is of the form: 
        {
            <class of other instances>: {
              <primary key of other instance>: [<field>, ...]
            }
        }
        '''
        
        results = {}
        def _results_add(other_model, other_instance, other_field):
            # It's important to store only the primary key since we 
            # don't want to have multiple in-memory instances of the same
            # object in the database
            pk = other_instance.pk
            if not other_model in results:
                results[other_model] = {}
            if not pk in results[other_model]:
                results[other_model][pk] = []
            results[other_model][pk].append(other_field)
        
        for ro in instance._meta.get_all_related_objects():
            # note that OneToOneFields are also ForeignKeys
            if isinstance(ro.field, models.OneToOneField):
                continue

            other_queryset = getattr(instance, ro.get_accessor_name())
            for other_instance in other_queryset.all():
                _results_add(ro.model, other_instance, ro.field)
        
        return results
    
    @staticmethod
    def _get_other_model_o2o_refs_to(instance):
        '''\
        Get every instance that isn't of the same model as the given instance, and has a OneToOneField that refers to the given instance. Return is of the form:
        {
            <class of other instance>: {
                <primary key of other instance>: [<field>, ...]
            }
        }
        '''
        
        results = {}
        def _results_add(other_model, other_instance, other_field):
            # It's important to store only the primary key since we 
            # don't want to have multiple in-memory instances of the same
            # object in the database
            pk = other_instance.pk
            if not other_model in results:
                results[other_model] = {}
            if not pk in results[other_model]:
                results[other_model][pk] = []
            results[other_model][pk].append(other_field)        
        
        for ro in instance._meta.get_all_related_objects():
            if not isinstance(ro.field, models.OneToOneField):
                continue
            # TODO this test really belongs in MergeForm.__init__
            if isinstance(instance, ro.model):
                raise NotImplementedError("can't merge Models with OneToOneFields references themselves.")
            
            # this may be the 'parent_link' field used to implement multi-
            # table inheritance.
            if ro.field.rel.parent_link:
                # if so, there must not be anything on the other side of
                # the relation, since that would mean this instance isn't
                # the most specific one
                # TODO this test really belongs in MergeForm.__init__
                try:
                    getattr(instance, ro.get_accessor_name())
                    # TODO not the best error message
                    raise ValueError("Can't merge instances of non-abstract superclasses unless there is no data for any subclass.")
                except ObjectDoesNotExist:
                    pass
            else:
                try:
                    other_instance = getattr(instance, ro.get_accessor_name())
                    _results_add(ro.model, other_instance, ro.field)
                except ObjectDoesNotExist:
                    pass
        
        return results
    
    @staticmethod
    def _get_o2o_refs_from(instance):
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
    
    @staticmethod
    def _get_m2m_refs_from(instance):
        '''
        Get all the instances referenced by the given instance in it's Model's ManyToManyFields. Return is of the form:
        {
            <field name>: (<other Model>, [<other instance primary key>, ...])
        }
        '''
        
        results = {}
        def _results_add(fieldname, other_model, other_instance):
            # It's important to store only the primary key since we 
            # don't want to have multiple in-memory instances of the same
            # object in the database
            pk = other_instance.pk
            if not fieldname in results.keys():
                results[fieldname] = (other_model, [])
            results[fieldname][1].append(pk)
        
        for field in instance._meta.fields:
            if isinstance(field, models.ManyToManyField):
                for other_instance in getattr(instance, field.name).all():
                    _results_add(field.name, other_instance.__class__, other_instance)
        
        return results
    
    @staticmethod
    def _get_m2m_refs_to(instance):
        '''
        Get all the instances that reference the given instance via a ManyToManyField in their Models. Return is of the form:
        {
            <model of other instance>: {
                <primary key of other instance>: [<field>, ...]
            }
        }
        '''
        
        results = {}
        def _results_add(other_model, other_instance, other_field):
            # It's important to store only the primary key since we 
            # don't want to have multiple in-memory instances of the same
            # object in the database
            pk = other_instance.pk
            if not other_model in results:
                results[other_model] = {}
            if not pk in results[other_model]:
                results[other_model][pk] = []
            results[other_model][pk].append(other_field)
        
        for ro in instance._meta.get_all_related_many_to_many_objects():
            other_queryset = getattr(instance, ro.get_accessor_name()).all()
            for other_instance in other_queryset:
                _results_add(
                    ro.model,
                    other_instance,
                    ro.field,
                )
        
        return results
    
    @staticmethod
    def _refs_to_display(instance):

        results = {}
        def _results_add(other_model, other_instance_pk, other_field):
            modelname = other_model._meta.verbose_name_plural
            if not modelname in results:
                results[modelname] = {}
            other_instance = other_model.objects.get(pk=other_instance_pk)
            if not other_instance in results[modelname]:
                results[modelname][other_instance] = []
            results[modelname][other_instance].append(other_field.verbose_name)
        
        # allow passing in of unsaved instances
        if not instance.pk:
            return results
        
        fk = MergeForm._get_fk_refs_to(instance)
        for model in fk.keys():
            for pk in fk[model]:
                for fieldname in fk[model][pk]:
                    _results_add(model, pk, fieldname)
        
        m2m = MergeForm._get_m2m_refs_to(instance)
        for model in m2m.keys():
            for pk in m2m[model]:
                for fieldname in m2m[model][pk]:
                    _results_add(model, pk, fieldname)
        
        return results
    
    # useful in templates
    def refs_to_source_display(self):
        return self._refs_to_display(self.source)
    
    # useful in templates
    def refs_to_destination_display(self):
        return self._refs_to_display(self.destination)
    
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
        
        # TODO start the transaction here? We're getting queryset of other
        # instances to display, then later saving changes to those instances.
        
        # OneToOneFields in the model we're merging need special handling. Since
        # they can only point to one other instance, we need merge forms for
        # the instance pointed to by the field in destination and source. We
        # also need to add a boolean field to the form to mark the 
        # OneToOneField as simply null in the destination.
        o2o_refs_from_source = self._get_o2o_refs_from(self.source)
        o2o_refs_from_destination = self._get_o2o_refs_from(self.destination)
        self.subforms = {}
        self.has_field_names = {}
        # avoid circular imports
        # TODO better place for this
        from cetacean_incidents.apps.locations.models import Location
        from cetacean_incidents.apps.locations.forms import LocationMergeForm
        from cetacean_incidents.apps.vessels.forms import VesselInfoMergeForm
        from cetacean_incidents.apps.vessels.models import VesselInfo
        from cetacean_incidents.apps.shipstrikes.forms import StrikingVesselInfoMergeForm
        from cetacean_incidents.apps.shipstrikes.models import StrikingVesselInfo
        from cetacean_incidents.apps.entanglements.forms import GearOwnerMergeForm
        from cetacean_incidents.apps.entanglements.models import GearOwner
        from cetacean_incidents.apps.entanglements.forms import LocationGearSetMergeForm
        from cetacean_incidents.apps.entanglements.models import LocationGearSet
        subform_classes = {
            Location: LocationMergeForm,
            VesselInfo: VesselInfoMergeForm,
            StrikingVesselInfo: StrikingVesselInfoMergeForm,
            GearOwner: GearOwnerMergeForm,
            LocationGearSet: LocationGearSetMergeForm,
        }
        
        # note that source_o2o_from_refs.key() will always be a subset of 
        # destination_o2o_from_refs.keys(), since we insured destination is an
        # instance of source.__class__
        for fieldname, field in o2o_refs_from_destination.items():
            # skip fields that were excluded
            if not fieldname in self.fields:
                continue
            
            destination_instance = getattr(destination, fieldname)
            if fieldname in o2o_refs_from_source.keys():
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
                raise NotImplementedError("%s needs a MergeForm subclass" % other_model)
            
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
    
    def is_valid(self):
        ok = super(MergeForm, self).is_valid()
        
        # check the subforms
        for fieldname, subform in self.subforms.items():
            if fieldname in self.has_field_names:
                has_field_name = self.has_field_names[fieldname]
                if has_field_name in self.cleaned_data:
                    if self.cleaned_data[has_field_name]:
                        ok = ok and subform.is_valid()
            else:
                ok = ok and subform.is_valid()
                
        return ok
    
    def save(self, commit=True):
        # FIXME uncommited saving is uncertain
        if not commit:
            raise NotImplementedError("uncommited saving of MergeForms is not yet implemented")
        
        if self.source.pk:
            # change refs to source to refs to destination
            refs_from = self._get_m2m_refs_to(self.source)
            for other_model in refs_from.keys():
                for other_pk, fields in refs_from[other_model].items():
                    other_obj = other_model.objects.get(pk=other_pk)
                    # make sure we're not instantiating an object for the source
                    # or destination
                    # TODO if other_obj == self.source, don't bother changing 
                    # anything
                    for obj in (self.destination, self.source):
                        if other_model == obj.__class__:
                            if not obj.pk is None:
                                if other_pk == obj.pk:
                                    other_obj = obj
                    for field in fields:
                        accessor = getattr(other_obj, field.name)
                        accessor.add(self.destination)
            
            refs_from = self._get_fk_refs_to(self.source)
            for other_model in refs_from.keys():
                for other_pk, fields in refs_from[other_model].items():
                    other_obj = other_model.objects.get(pk=other_pk)
                    # make sure we're not instantiating an object for the source
                    # or destination
                    for obj in (self.destination, self.source):
                        if other_model == obj.__class__:
                            if not obj.pk is None:
                                if other_pk == obj.pk:
                                    other_obj = obj
                    for field in fields:
                        # switch fk refs from the source to the destination
                        setattr(other_obj, field.name, self.destination)
                    other_obj.save()
            
        # handle o2o refs from this model
        for fieldname in self.subforms.keys():
            if fieldname in self.has_field_names:
                has_field_name = self.has_field_names[fieldname]
                if not self.cleaned_data[has_field_name]:
                    setattr(self.destination, fieldname, None)
                else:
                    saved_instance = self.subforms[fieldname].save()
                    # TODO is this setattr call necessary?
                    setattr(self.destination, fieldname, saved_instance)
            else:
                saved_instance = self.subforms[fieldname].save()
                # TODO is this setattr call necessary?
                setattr(self.destination, fieldname, saved_instance)
        
        result = super(MergeForm, self).save(commit=commit)
        
        return result

    def delete(self):
        '''\
        save() saves the destination, delete() deletes the source
        '''
        
        if self.source.pk:
            # change refs to source to refs to destination
            # don't remove self.source from m2m refs to it. the references
            # will disappear when it is deleted.
            
            if False:
                refs_from = self._get_m2m_refs_to(self.source)
                for other_model in refs_from.keys():
                    for other_pk, fields in refs_from[other_model].items():
                        other_obj = other_model.objects.get(pk=other_pk)
                        # make sure we're not instantiating an object for the 
                        # source or destination
                        # TODO if other_obj == self.source, don't bother 
                        # changing anything
                        for obj in (self.destination, self.source):
                            if other_model == obj.__class__:
                                if not obj.pk is None:
                                    if other_pk == obj.pk:
                                        other_obj = obj
                        for field in fields:
                            accessor = getattr(other_obj, field.name)
                            accessor.remove(self.source)
            
            # set o2o refs to self.source to None
            refs_from = self._get_other_model_o2o_refs_to(self.source)
            for other_model in refs_from.keys():
                for other_pk, fields in refs_from[other_model].items():
                    other_obj = other_model.objects.get(pk=other_pk)
                    # make sure we're not instantiating an object for the source
                    # or destination
                    for obj in (self.destination, self.source):
                        if other_model == obj.__class__:
                            if not obj.pk is None:
                                if other_pk == obj.pk:
                                    other_obj = obj
                    for field in fields:
                        try:
                            # set o2o refs to the source to None, if possible
                            setattr(other_obj, field.name, None)
                        except ValueError:
                            pass
                    other_obj.save()
            
        if self.source.pk:
            self.source.delete()

        # handle o2o refs from this model
        for fieldname in self.subforms.keys():
            self.subforms[fieldname].delete()

